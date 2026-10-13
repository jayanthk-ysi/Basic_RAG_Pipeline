from pathlib import Path

from huggingface_hub import snapshot_download

MODELS_DIR = Path(__file__).resolve().parent / "models"


def ensure_model(repo_id: str) -> str:
    # Returns a local folder for the model; downloads it only if it isn't there yet.
    local_dir = MODELS_DIR / repo_id.replace("/", "__")
    marker = local_dir / ".download_complete"   # written only after a full download, so a half-finished one is resumed

    if marker.exists():
        print(f"Using local copy of {repo_id}")
    else:
        print(f"Downloading {repo_id} to {local_dir} ...")
        snapshot_download(repo_id=repo_id, local_dir=str(local_dir))
        marker.touch()

    return str(local_dir)
