#!/usr/bin/env python3
"""Upload ALL workspace files to GitHub via REST API (HTTP/1.1)."""
import base64
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

WORKSPACE = Path(".")
REPO = "aethersery/addon-generator"

TOKEN = Path(".gh_token.txt").read_text().strip()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "Python-urllib",
}

IGNORE_DIRS = {".git", ".harness", "__pycache__", "node_modules", ".next", ".venv"}
IGNORE_SUFFIXES = (
    ".pyc", ".pyo", ".log", ".mcaddon", ".zip", ".db", ".sqlite3",
    ".tmp", ".temp", ".DS_Store",
)
IGNORE_NAMES = {
    ".env", ".gitignore", "install_log.txt", "install_fastapi.py",
    "test_error.txt", "test_out.txt", "test_output.txt",
}.union({f"run_pip_install{i}.py" for i in range(1, 10)}).union({f"pip_install{i}.log" for i in range(1, 10)})


def should_ignore(path: Path) -> bool:
    parts = path.parts
    for d in IGNORE_DIRS:
        if d in parts:
            return True
    name = path.name
    if name in IGNORE_NAMES:
        return True
    for suf in IGNORE_SUFFIXES:
        if name.endswith(suf):
            return True
    return False


def collect_files():
    files = []
    for root, dirs, filenames in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for fn in sorted(filenames):
            fpath = Path(root) / fn
            if should_ignore(fpath):
                continue
            rel = str(fpath.relative_to(WORKSPACE))
            files.append((rel, fpath))
    return files


def put_file(rel, content_b64):
    url = f"https://api.github.com/repos/{REPO}/contents/{rel}"
    payload = json.dumps({"message": f"Add {rel}", "content": content_b64}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=HEADERS, method="PUT")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()[:80]
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()[:80]
        except Exception:
            body = str(e)
        return e.code, body
    except Exception as e:
        return "ERR", str(e)[:80]


def main():
    files = collect_files()
    print(f"Arquivos para enviar: {len(files)}")
    ok = fail = 0
    for i, (rel, fpath) in enumerate(files, 1):
        try:
            raw = fpath.read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
        except Exception as e:
            print(f"  [{i}/{len(files)}] SKIP (leitura): {rel} - {e}")
            continue

        code, body = put_file(rel, b64)
        if code in (200, 201):
            ok += 1
            print(f"  [{i}/{len(files)}] OK [{code}]: {rel}")
        else:
            fail += 1
            print(f"  [{i}/{len(files)}] FALHA [{code}]: {rel} - {body}")

    print(f"\nResultado: {ok} OK, {fail} falha(s), {len(files)} total")


if __name__ == "__main__":
    main()
