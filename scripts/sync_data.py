#!/usr/bin/env python3
import shutil
import sys
from pathlib import Path

root = Path(__file__).parent.parent.parent
source = root / "database" / "outputs"
targets = {
    "app": root / "app" / "assets" / "data",
    "server": root / "server" / "data",
}

def sync_server_media(dst: Path) -> None:
    media_dst = dst / "media"
    shutil.rmtree(media_dst, ignore_errors=True)

    for level_dir in source.iterdir():
        level = level_dir.name
        level_db = level_dir / f"{level}.db"

        if level_db.exists():
            shutil.rmtree(dst / level, ignore_errors=True)
            (dst / level).mkdir(parents=True)
            shutil.copy2(level_db, dst / level)

        for folder_name in ("audios", "images"):
            media_folder = level_dir / folder_name
            if media_folder.exists():
                shutil.copytree(media_folder, media_dst / level, dirs_exist_ok=True)


target = sys.argv[1] if len(sys.argv) > 1 else "all"
to_sync = targets if target == "all" else {target: targets.get(target)}

if not source.exists() or (target != "all" and target not in targets):
    sys.exit(1)

for name, dst in to_sync.items():
    if name == "server":
        sync_server_media(dst)
        continue

    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dst)
