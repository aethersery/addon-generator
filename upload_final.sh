#!/bin/bash
# Upload ALL workspace files to GitHub using gh api
TOKEN=$(cat .token.txt | tr -d '\n')
export GH_TOKEN="$TOKEN"
REPO="aethersery/addon-generator"

IGNORE_DIRS=".git .harness __pycache__ node_modules .next .venv"
IGNORE_SUFFIXES=".pyc .pyo .log .mcaddon .zip .db .sqlite3 .tmp .temp .DS_Store"
IGNORE_NAMES=".env .gitignore install_log.txt install_fastapi.py test_error.txt test_out.txt test_output.txt upload_all.py upload_gh.sh upload_to_github.py test_upload.py TEST.txt TEST2.txt test_curl.txt test_env.txt test_direct.txt test_env2.txt test_printf.txt test_inline.txt test_ghenv.txt .token.txt .env_token output.txt"

count=0
ok=0
fail=0
skipped=0

while IFS= read -r f; do
    skip=0
    for d in $IGNORE_DIRS; do
        if echo "$f" | grep -q "/$d/"; then skip=1; break; fi
    done
    [ "$skip" = "1" ] && continue

    fname=$(basename "$f")
    
    for suf in $IGNORE_SUFFIXES; do
        case "$fname" in
            *$suf) skip=1; break;;
        esac
    done
    [ "$skip" = "1" ] && continue
    
    for nm in $IGNORE_NAMES; do
        [ "$fname" = "$nm" ] && skip=1 && break
    done
    [ "$skip" = "1" ] && continue

    rel="${f#./}"
    
    content=$(base64 -w0 "$f" 2>/dev/null)
    [ -z "$content" ] && continue

    json_content=$(echo "$content" | sed 's/\\/\\\\/g; s/"/\\"/g')
    
    gh api --method PUT "repos/$REPO/contents/$rel" \
        -f message="Add $rel" \
        -f content="$json_content" \
        > /dev/null 2>&1
    
    count=$((count + 1))
    if [ $? -eq 0 ]; then
        ok=$((ok + 1))
        echo "OK: $rel"
    else
        fail=$((fail + 1))
        echo "FALHA: $rel"
    fi
done < <(find . -type f | sort)

echo ""
echo "Total: $count | OK: $ok | Falha: $fail | Pulos: $skipped"
