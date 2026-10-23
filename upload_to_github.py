#!/usr/bin/env python3
"""Envia todos os arquivos do workspace para o GitHub via REST API."""
import base64
import json
import os
from pathlib import Path

import requests

WORKSPACE = Path("/storage/emulated/0/Android/data/com.androidharness.app/files/workspace")
REPO = "aethersery/addon-generator"
TOKEN = os.environ.get("GH_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Arquivos/pastas a IGNORAR (mesmo do .gitignore)
IGNORE_NAMES = {
    ".git", ".harness", "__pycache__", "node_modules", ".next", ".venv", ".env",
    "*.pyc", "*.pyo", "*.log", "*.mcaddon", "*.zip", "*.db", "*.sqlite3",
    "*.tmp", "*.temp", "test_*.py", "test_*.txt", "pip_install*.log",
    "install_log.txt", "install_fastapi.py", "run_pip_install*.py",
    ".DS_Store", "Thumbs.db", "desktop.ini",
}
IGNORE_DIRS = {".git", ".harness", "__pycache__", "node_modules", ".next", ".venv"}


def should_ignore(path: Path) -> bool:
    name = path.name
    if name in IGNORE_NAMES:
        return True
    for pat in ("*.log", "*.mcaddon", "*.zip", "*.tmp", "*.temp"):
        if path.match(pat):
            return True
    if any(part in IGNORE_DIRS for part in path.parts):
        return True
    return False


def collect_files():
    """Coleta todos os arquivos relevantes do workspace."""
    files = []
    for root, dirs, filenames in os.walk(WORKSPACE):
        # Filtra diretorios ignorados
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for fn in filenames:
            fpath = Path(root) / fn
            rel = fpath.relative_to(WORKSPACE)
            if should_ignore(fpath):
                continue
            files.append((str(rel), fpath))
    return sorted(files)


def b64(content: str) -> str:
    return base64.b64encode(content.encode("utf-8")).decode("ascii")


def create_file(rel_path: str, content: str):
    url = f"https://api.github.com/repos/{REPO}/contents/{rel_path}"
    data = {
        "message": f"Add {rel_path}",
        "content": b64(content),
    }
    r = requests.put(url, headers=HEADERS, json=data)
    return r


def main():
    files = collect_files()
    print(f"Total de arquivos para enviar: {len(files)}")
    ok = 0
    fail = 0
    for rel, fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Arquivo binário - pula
            print(f"  SKIP (binário): {rel}")
            continue
        except Exception as e:
            print(f"  SKIP (erro leitura): {rel} - {e}")
            continue

        r = create_file(rel, content)
        if r.status_code in (201, 200):
            ok += 1
            print(f"  OK: {rel}")
        else:
            fail += 1
            print(f"  FALHA ({r.status_code}): {rel} - {r.text[:120]}")

    print(f"\nResultado: {ok} OK, {fail} falha(s), {len(files)} total")


if __name__ == "__main__":
    main()
