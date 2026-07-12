import os
import sys
import shutil
import subprocess
import json
import time
import stat
from collections import Counter

# Configuration
REMOTE_URL = "https://github.com/Hardik182005/CollabForge-AI"
BATCH_SIZE = 15
DELAY_MINUTES = 30
STATE_FILE = os.path.join(os.path.dirname(__file__), "git_dripper_state.json")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_DIR_PATH = os.path.join(REPO_DIR, ".git_temp")

# Configure environment variables to use .git_temp as the git directory
# and the project directory as the working tree. This bypasses Windows locks on the default .git folder.
os.environ["GIT_DIR"] = GIT_DIR_PATH
os.environ["GIT_WORK_TREE"] = REPO_DIR

def run_git(args, cwd=REPO_DIR):
    """Run a git command and return its stdout, or raise an error."""
    cmd = ["git"] + args
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=os.environ)
    if result.returncode != 0:
        print(f"Git command failed: {' '.join(cmd)}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result.stdout.strip()

def remove_readonly(func, path, excinfo):
    """OnError handler for shutil.rmtree to remove read-only attribute."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clean_git_directory():
    """Delete the local .git_temp directory if it exists."""
    if os.path.exists(GIT_DIR_PATH):
        print(f"Removing existing .git_temp folder at {GIT_DIR_PATH}...")
        shutil.rmtree(GIT_DIR_PATH, onerror=remove_readonly)
        print("Existing .git_temp folder removed successfully.")

def initialize_repository():
    """Initialize a clean repository and set up the remote."""
    print("Initializing clean Git repository in .git_temp...")
    run_git(["init"])
    run_git(["checkout", "-b", "main"])
    run_git(["remote", "add", "origin", REMOTE_URL])
    print(f"Remote origin set to {REMOTE_URL}")

def get_all_project_files():
    """Stage all files temporarily to let Git filter gitignored files, then unstage them."""
    print("Staging all files to determine tracked file list...")
    run_git(["add", "-A"])
    status_output = run_git(["status", "--porcelain"])
    run_git(["reset"])
    
    files = []
    for line in status_output.splitlines():
        # Line format: 'A  "file path"' or 'A  file_path'
        if len(line) > 3:
            path = line[3:].strip()
            # Remove enclosing quotes if present
            if path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
            # Replace backslashes with forward slashes for git compatibility
            path = path.replace("\\", "/")
            # Exclude state file, the script itself, and any temporary git metadata from commits
            if "git_dripper_state.json" in path or "git_dripper.py" in path or ".git_temp" in path or ".git/" in path:
                continue
            files.append(path)
            
    print(f"Found {len(files)} files to track (respecting .gitignore).")
    return sorted(files)

def generate_commit_message(files):
    """Generate a realistic, human-like commit message based on the files in the batch."""
    categories = []
    for f in files:
        f_lower = f.lower()
        if "backend/config" in f_lower or f_lower.endswith(".env") or "apprunner.yaml" in f_lower:
            categories.append("backend-config")
        elif "backend/controllers" in f_lower or "backend/routes" in f_lower or "backend/services" in f_lower:
            categories.append("backend-api")
        elif "backend/models" in f_lower:
            categories.append("backend-models")
        elif "frontend/css" in f_lower or f_lower.endswith(".css"):
            categories.append("frontend-styles")
        elif "frontend/js/views" in f_lower:
            categories.append("frontend-views")
        elif "frontend/js/core" in f_lower or "frontend/js/api" in f_lower or f_lower.endswith(".js"):
            categories.append("frontend-core")
        elif f_lower.endswith(".md") or "docs/" in f_lower:
            categories.append("docs")
        elif "docker" in f_lower:
            categories.append("docker")
        else:
            categories.append("misc")
            
    most_common, count = Counter(categories).most_common(1)[0]
    
    # Specific realistic commit messages
    if most_common == "backend-config":
        return "chore: configure backend server settings and database connection"
    elif most_common == "backend-api":
        return "feat: implement backend API controllers and service layer"
    elif most_common == "backend-models":
        return "feat: define database schemas and data models"
    elif most_common == "frontend-styles":
        return "style: implement global layout, colors and typography styles"
    elif most_common == "frontend-views":
        return "feat: create responsive dashboard views and modular components"
    elif most_common == "frontend-core":
        return "feat: implement frontend state management and API integration"
    elif most_common == "docs":
        return "docs: update README and setup documentation"
    elif most_common == "docker":
        return "chore: add Dockerfile and docker-compose configurations"
    else:
        # Fallback to directory-based naming
        sample_dir = os.path.dirname(files[0]) if files else ""
        if sample_dir:
            return f"feat: add core files for {sample_dir} module"
        return "feat: set up project structure and initial assets"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def try_rename_git_dir():
    """Try to rename .git_temp to .git once done."""
    git_dir = os.path.join(REPO_DIR, ".git")
    
    # Clear environment variables so they don't block
    if "GIT_DIR" in os.environ:
        del os.environ["GIT_DIR"]
    if "GIT_WORK_TREE" in os.environ:
        del os.environ["GIT_WORK_TREE"]

    print("\nAttempting to rename .git_temp to standard .git directory...")
    
    # If the old tombstoned .git folder is still there, try to delete it
    if os.path.exists(git_dir):
        try:
            shutil.rmtree(git_dir, onerror=remove_readonly)
        except Exception:
            pass
            
    try:
        os.rename(GIT_DIR_PATH, git_dir)
        print("Success! The repository is now configured as a standard .git repository.")
    except Exception as e:
        print("\n[WARNING] Could not rename .git_temp to .git automatically (likely due to active IDE locks).")
        print("Your repository is fully pushed to GitHub!")
        print("To finish local setup:")
        print("1. Close the IDE or restart your PC.")
        print("2. Delete the old '.git' folder (if it still exists).")
        print("3. Rename '.git_temp' to '.git'.")

def run_drip_feed():
    state = load_state()
    
    if not state:
        print("Starting fresh commit process...")
        clean_git_directory()
        initialize_repository()
        all_files = get_all_project_files()
        
        # Batch the files
        batches = [all_files[i:i + BATCH_SIZE] for i in range(0, len(all_files), BATCH_SIZE)]
        print(f"Split {len(all_files)} files into {len(batches)} batches of {BATCH_SIZE} files.")
        
        state = {
            "total_files": len(all_files),
            "total_batches": len(batches),
            "current_batch_index": 0,
            "batches": batches,
            "committed_batches": []
        }
        save_state(state)
    else:
        print(f"Resuming existing session. Completed {len(state['committed_batches'])}/{state['total_batches']} batches.")
        # Ensure the repo is initialized if we are resuming
        if not os.path.exists(GIT_DIR_PATH):
            print("Local .git_temp directory was missing. Reinitializing...")
            initialize_repository()

    while state["current_batch_index"] < state["total_batches"]:
        idx = state["current_batch_index"]
        batch = state["batches"][idx]
        
        print(f"\n--- Processing Batch {idx + 1}/{state['total_batches']} ({len(batch)} files) ---")
        
        # Add files in this batch
        for f in batch:
            if os.path.exists(os.path.join(REPO_DIR, f)):
                # Use --force if we need to add files that might be matched by generic exclude rules but we want them tracked
                run_git(["add", f])
            else:
                print(f"Warning: file not found: {f}")
                
        # Commit
        msg = generate_commit_message(batch)
        print(f"Committing with message: '{msg}'")
        run_git(["commit", "-m", msg])
        
        # Push
        print("Pushing to remote GitHub repository...")
        try:
            if idx == 0:
                # Force push on first batch to overwrite any existing history on GitHub
                run_git(["push", "-u", "origin", "main", "--force"])
            else:
                run_git(["push", "origin", "main"])
            print("Successfully pushed to GitHub.")
        except subprocess.CalledProcessError as e:
            print(f"Error during push: {e}. Retrying in 10 seconds...")
            time.sleep(10)
            if idx == 0:
                run_git(["push", "-u", "origin", "main", "--force"])
            else:
                run_git(["push", "origin", "main"])
                
        # Update State
        state["committed_batches"].append(idx)
        state["current_batch_index"] += 1
        save_state(state)
        
        # If there are more batches, sleep for 30 minutes with a countdown timer
        if state["current_batch_index"] < state["total_batches"]:
            wait_seconds = BATCH_SIZE if os.environ.get("TEST_DRIPPER") else DELAY_MINUTES * 60
            print(f"Waiting {DELAY_MINUTES if not os.environ.get('TEST_DRIPPER') else 'seconds'} before committing the next batch...")
            
            # Nice dynamic countdown
            step = 1 if os.environ.get("TEST_DRIPPER") else 10
            for remaining in range(wait_seconds, 0, -step):
                mins = remaining // 60
                secs = remaining % 60
                sys.stdout.write(f"\rNext commit in {mins:02d}m {secs:02d}s...")
                sys.stdout.flush()
                time.sleep(step)
            print("\rCountdown completed. Proceeding to next batch.")
            
    print("\nAll batches have been successfully committed and pushed to GitHub!")
    try_rename_git_dir()
    
    # Optionally delete state file on completion
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

if __name__ == "__main__":
    try:
        run_drip_feed()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. State saved. Run script again to resume.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        sys.exit(1)
