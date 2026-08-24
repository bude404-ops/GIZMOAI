from pathlib import Path
import re

PATTERNS = [
    re.compile("github" + r"_pat_[A-Za-z0-9_]+"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile("PRIVATE" + r" KEY"),
    re.compile("BEGIN" + r" RSA"),
]
SKIP_PARTS = {".git", ".pytest_cache", "__pycache__", ".gizmo_runtime"}
SKIP_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3"}
findings = []
for path in Path('.').rglob('*'):
    if path.is_dir() or any(part in SKIP_PARTS for part in path.parts) or path.suffix in SKIP_SUFFIXES:
        continue
    text = path.read_text(errors='ignore')
    for pattern in PATTERNS:
        if pattern.search(text):
            findings.append((str(path), pattern.pattern))
if findings:
    raise SystemExit(f"Secret scan failed: {findings}")
print("Secret scan passed")
