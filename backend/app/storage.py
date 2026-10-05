from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2] / "uploads"

def store_bytes(meeting_id: str, filename: str, content: bytes) -> str:
    target_dir = ROOT / meeting_id
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4()}-{Path(filename).name}"
    target = target_dir / safe_name
    target.write_bytes(content)
    return str(target)
