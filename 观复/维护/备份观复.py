"""检查观复并覆盖唯一的一份库外快照；--verify 只校验现有快照。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT.parents[1] / "Documents" / "观复备份" / "观复.zip"
MANIFEST = "__manifest__.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory() -> tuple[list[Path], list[Path]]:
    entries = sorted(ROOT.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("知识库包含符号链接，需先确认其实际内容")
    files = [path for path in entries if path.is_file()]
    dirs = [path for path in entries if path.is_dir()]
    if any(path.relative_to(ROOT).as_posix() == MANIFEST for path in files):
        raise ValueError(f"知识库根目录已有保留文件名 {MANIFEST}")
    return files, dirs


def make_zip(target: Path) -> None:
    files, dirs = inventory()
    records = []
    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in dirs:
            archive.writestr(path.relative_to(ROOT).as_posix() + "/", b"")
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(name, data)
            records.append({"path": name, "bytes": len(data), "sha256": digest(data)})
        manifest = {
            "root": ROOT.name,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "files": records,
            "directories": [path.relative_to(ROOT).as_posix() + "/" for path in dirs],
        }
        archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def verify_zip(path: Path) -> dict:
    with ZipFile(path, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"压缩包损坏：{bad}")
        manifest = json.loads(archive.read(MANIFEST))
        files = manifest["files"]
        expected = {MANIFEST} | {item["path"] for item in files} | set(manifest["directories"])
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
            raise ValueError("压缩包文件清单不一致")
        for item in files:
            data = archive.read(item["path"])
            if len(data) != item["bytes"] or digest(data) != item["sha256"]:
                raise ValueError(f"文件校验失败：{item['path']}")
        return manifest


def main() -> None:
    if sys.argv[1:] == ["--verify"]:
        manifest = verify_zip(BACKUP)
        print(f"快照校验通过：{BACKUP}，{len(manifest['files'])} 个文件")
        return
    if len(sys.argv) != 1:
        raise ValueError("用法：python 备份观复.py [--verify]")

    check = subprocess.run(
        [sys.executable, str(ROOT / "维护" / "检查知识库.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    print(check.stdout, end="")
    if check.returncode:
        print(check.stderr, end="", file=sys.stderr)
        raise RuntimeError("知识库检查未通过；旧快照未被覆盖")

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="观复-", suffix=".partial", dir=BACKUP.parent, delete=False) as handle:
            temporary = Path(handle.name)
        make_zip(temporary)
        manifest = verify_zip(temporary)
        os.replace(temporary, BACKUP)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"快照已更新并校验：{BACKUP}，{len(manifest['files'])} 个文件")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"备份失败：{exc}", file=sys.stderr)
        sys.exit(1)
