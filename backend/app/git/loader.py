import git
import tempfile
import os
import shutil

def clone_repository(repo_url: str) -> str:
    """Clones a repository to a temp dir and returns the path."""
    temp_dir = tempfile.mkdtemp()
    try:
        git.Repo.clone_from(repo_url, temp_dir)
        return temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir)
        raise e

def get_code_content(repo_path: str, extensions=[".py", ".js", ".html", ".css"]) -> str:
    """Reads code files from the repo."""
    content = ""
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content += f"\n--- {file} ---\n"
                        content += f.read()
                except Exception:
                    continue # Skip binary or unreadable files
    return content

def clean_up(repo_path: str):
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)


