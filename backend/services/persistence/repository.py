"""Campaign Room persistence: DynamoDB in production, JSON files locally.

Both drivers implement the same four methods so routes never branch.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalRepository:
    """JSON-file store for local development."""

    def __init__(self, path: Optional[str] = None):
        self.dir = os.path.abspath(path or os.path.join(settings.LOCAL_STORAGE_PATH, "campaigns"))
        os.makedirs(self.dir, exist_ok=True)

    def _file(self, campaign_id: str) -> str:
        safe = "".join(c for c in campaign_id if c.isalnum() or c in "-_")
        return os.path.join(self.dir, f"{safe}.json")

    def create(self, data: dict) -> dict:
        cid = str(uuid.uuid4())
        record = {"campaign_id": cid, "created_at": _now(), "updated_at": _now(), **data}
        with open(self._file(cid), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        return record

    def get(self, campaign_id: str) -> Optional[dict]:
        try:
            with open(self._file(campaign_id), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def update(self, campaign_id: str, data: dict) -> Optional[dict]:
        rec = self.get(campaign_id)
        if not rec:
            return None
        rec.update(data)
        rec["updated_at"] = _now()
        rec["campaign_id"] = campaign_id
        with open(self._file(campaign_id), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        return rec

    def list(self, limit: int = 50) -> list:
        out = []
        try:
            names = sorted(os.listdir(self.dir), reverse=True)
        except OSError:
            return []
        for name in names[: limit * 2]:
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.dir, name), encoding="utf-8") as f:
                    rec = json.load(f)
                out.append({k: rec.get(k) for k in ("campaign_id", "name", "created_at", "updated_at", "status")})
            except (OSError, json.JSONDecodeError):
                continue
        out.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return out[:limit]


class DynamoRepository:
    """Single-table DynamoDB store (pk=CAMPAIGN#{id}). Uses the App Runner
    instance role — no keys in code."""

    def __init__(self):
        import boto3  # imported lazily so local dev doesn't need boto3
        self.table = boto3.resource(
            "dynamodb", region_name=settings.AWS_REGION or None
        ).Table(settings.AWS_DYNAMODB_TABLE)

    @staticmethod
    def _ser(data: dict) -> dict:
        # DynamoDB rejects float; round-trip through JSON with Decimal parsing.
        from decimal import Decimal
        return json.loads(json.dumps(data), parse_float=Decimal)

    @staticmethod
    def _deser(item: dict) -> dict:
        from decimal import Decimal

        def conv(o):
            if isinstance(o, Decimal):
                return int(o) if o == o.to_integral_value() else float(o)
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            if isinstance(o, list):
                return [conv(v) for v in o]
            return o
        return conv(item)

    def create(self, data: dict) -> dict:
        cid = str(uuid.uuid4())
        record = {"campaign_id": cid, "created_at": _now(), "updated_at": _now(), **data}
        item = {"pk": f"CAMPAIGN#{cid}", "sk": "ROOM", **self._ser(record)}
        self.table.put_item(Item=item)
        return record

    def get(self, campaign_id: str) -> Optional[dict]:
        resp = self.table.get_item(Key={"pk": f"CAMPAIGN#{campaign_id}", "sk": "ROOM"})
        item = resp.get("Item")
        if not item:
            return None
        item.pop("pk", None); item.pop("sk", None)
        return self._deser(item)

    def update(self, campaign_id: str, data: dict) -> Optional[dict]:
        rec = self.get(campaign_id)
        if not rec:
            return None
        rec.update(data)
        rec["updated_at"] = _now()
        rec["campaign_id"] = campaign_id
        self.table.put_item(Item={"pk": f"CAMPAIGN#{campaign_id}", "sk": "ROOM", **self._ser(rec)})
        return rec

    def list(self, limit: int = 50) -> list:
        resp = self.table.scan(Limit=200)
        rooms = [self._deser(i) for i in resp.get("Items", []) if i.get("sk") == "ROOM"]
        out = [{k: r.get(k) for k in ("campaign_id", "name", "created_at", "updated_at", "status")} for r in rooms]
        out.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return out[:limit]


def get_repository():
    if settings.DATABASE_MODE == "dynamodb" and settings.AWS_DYNAMODB_TABLE:
        return DynamoRepository()
    return LocalRepository()
