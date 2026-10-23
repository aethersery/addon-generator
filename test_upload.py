import urllib.request, base64, json

TOKEN = open(".gh_token.txt").read().strip()
H = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "Python",
}
REPO = "aethersery/addon-generator"

def create_file(path, content_b64, message):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    data = json.dumps({"message": message, "content": content_b64}).encode()
    req = urllib.request.Request(url, data=data, headers=H, method="PUT")
    try:
        r = urllib.request.urlopen(req)
        return r.status, r.read().decode()[:100]
    except Exception as e:
        msg = ""
        if hasattr(e, "read"):
            try: msg = e.read().decode()[:100]
            except: pass
        return getattr(e, 'code', 'ERR'), msg

# Teste simples
status, body = create_file("TEST.txt", base64.b64encode(b"hello").decode(), "test")
print(f"Status: {status}, Body: {body}")
