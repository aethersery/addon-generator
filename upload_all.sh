#!/bin/bash
# Envia todos os arquivos do workspace para o GitHub via API
TOKEN=$(cat .gh_token.txt)
REPO="aethersery/addon-generator"
WORKSPACE="."

IGNORE_DIRS=".git .harness __pycache__ node_modules .next .venv"
IGNORE_NAMES=".env *.pyc *.pyo *.log *.mcaddon *.zip *.db *.sqlite3 *.tmp *.temp test_*.py test_*.txt pip_install*.log install_log.txt install_fastapi.py run_pip_install*.py .DS_Store Thumbs.db desktop.ini"

count=0
ok=0
fail=0

for f in $(find "$WORKSPACE" -type f | sort); do
    # Pula diretorios ignorados
    skip=0
    for d in $IGNORE_DIRS; do
        if echo "$f" | grep -q "/$d/"; then skip=1; break; fi
    done
    if [ "$skip" = "1" ]; then continue; fi

    # Pula nomes ignorados
    fname=$(basename "$f")
    for pat in $IGNORE_NAMES; do
        # Simples match por sufixo
        case "$fname" in
            $pat) skip=1; break;;
        esac
    done
    if [ "$skip" = "1" ]; then continue; fi

    # Caminho relativo sem ./
    rel="${f#./}"

    # Lê arquivo e faz base64
    content=$(base64 -w0 "$f")
    if [ -z "$content" ]; then continue; fi

    # Escapa aspas duplas no content para JSON
    json="{\"message\":\"Add $rel\",\"content\":\"$content\"}"

    code=$(curl --http1.1 -s -o /dev/null -w "%{http_code}" \
        -X PUT "https://api.github.com/repos/$REPO/contents/$rel" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        -d "$json" 2>/dev/null)

    count=$((count + 1))
    if [ "$code" = "201" ] || [ "$code" = "200" ]; then
        ok=$((ok + 1))
        echo "OK [$code]: $rel"
    else
        fail=$((fail + 1))
        echo "FALHA [$code]: $rel"
    fi

    # Pequena pausa para não sobrecarregar a API
    sleep 0.2
done

echo ""
echo "Total: $count | OK: $ok | Falha: $fail"
