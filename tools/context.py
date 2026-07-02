_repo_path = None

def set_repo_path(path: str):
    global _repo_path
    _repo_path = path

def get_repo_path() -> str:
    if _repo_path is None:
        raise ValueError("repo_path not set — call set_repo_path first")
    return _repo_path