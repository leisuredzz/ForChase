from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKIP = {".obsidian", ".workbuddy", "待入库"}
ATTACHMENTS = {"附件"}
VERIFY_LABELS = ("已实测", "部分实测", "文档核对", "未核验", "不适用")
notes = [
    path for path in ROOT.rglob("*.md")
    if not any(part in SKIP for part in path.relative_to(ROOT).parts)
]
all_files = [
    path for path in ROOT.rglob("*") if path.is_file()
    and not any(part in SKIP for part in path.relative_to(ROOT).parts)
]
reference_files = [path for path in ROOT.rglob("*") if path.is_file() and ".obsidian" not in path.relative_to(ROOT).parts and ".workbuddy" not in path.relative_to(ROOT).parts]
names = Counter(path.name for path in reference_files)
stems = Counter(path.stem for path in notes)
link_stems = Counter(path.stem for path in reference_files if path.suffix.lower() == ".md")
issues: list[str] = []

for name, count in stems.items():
    if count > 1:
        issues.append(f"重复笔记名：{name} × {count}")

for path in notes:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    h1 = []
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        marker = re.match(r"^\s*(?:-\s*)?(`{3,}|~{3,})", line)
        if marker:
            fenced = not fenced
            continue
        if fenced:
            continue
        if line.startswith("# "):
            h1.append(number)
        link_line = re.sub(r"(`+).*?\1", "", line)
        for target in re.findall(r"\[\[([^\]]+)\]\]", link_line):
            target = target.split("|", 1)[0].split("#", 1)[0]
            path_target = ROOT / target.replace("\\", "/")
            if target and not path_target.is_file() and names[target] == 0 and link_stems[target] == 0:
                issues.append(f"{rel}:{number} 缺失内部链接：{target}")
        if re.search(r"!\[[^\]]*\]\([A-Za-z]:\\|<img[^>]+src=[\"'][A-Za-z]:\\", line):
            issues.append(f"{rel}:{number} 使用库外绝对图片路径")
    if fenced:
        issues.append(f"{rel} 代码围栏未闭合")
    if len(h1) != 1:
        issues.append(f"{rel} 一级标题数量为 {len(h1)}")
    if rel.parts[0][:1].isdigit():
        status = next(
            (
                line.split("：", 1)[1].strip()
                for line in text.splitlines()
                if line.startswith("> **核验状态**：")
            ),
            None,
        )
        if status is None:
            issues.append(f"{rel} 缺少核验状态行：> **核验状态**：…")
        elif not any(status.startswith(label) for label in VERIFY_LABELS):
            issues.append(f"{rel} 核验状态取值不在规定范围：{status[:24]}")

attachments = [
    path for path in all_files
    if any(part in ATTACHMENTS for part in path.relative_to(ROOT).parts)
]
for path in all_files:
    relative = path.relative_to(ROOT)
    if path.suffix.lower() == ".md" or relative.parts[0] == "附件":
        continue
    if relative.parts[0] == "维护" and path.suffix.lower() == ".py":
        continue
    issues.append(f"非 Markdown 材料未归入附件：{relative}")
note_texts = [path.read_text(encoding="utf-8") for path in notes]
linked_targets = {
    target.split("|", 1)[0].split("#", 1)[0].replace("\\", "/")
    for text in note_texts
    for target in re.findall(r"\[\[([^\]]+)\]\]", text)
}
linked_targets.update(
    unquote(target.strip("<>").split("#", 1)[0]).replace("\\", "/")
    for text in note_texts
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
)
for attachment in attachments:
    relative_name = attachment.relative_to(ROOT).as_posix()
    if not any(target == attachment.name or target.endswith("/" + relative_name) or target == relative_name for target in linked_targets):
        issues.append(f"未被任何笔记引用的附件：{attachment.relative_to(ROOT)}")

print(f"主知识区：{len(notes)} 篇 Markdown，{len(all_files)} 个文件，{len(attachments)} 个附件")
if issues:
    for issue in issues:
        print("问题：", issue)
    sys.exit(1)
print("结构检查通过：内部链接、唯一标题、代码围栏、附件引用、附件位置、图片路径、核验状态行")
