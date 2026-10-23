import subprocess
import sys

with open('/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/pip_install.log', 'w') as log:
    log.write("Starting pip install...\n")
    log.flush()
    
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', 'fastapi', 'pydantic', 'pydantic-settings', 'python-dotenv', 'httpx'],
        stdout=log,
        stderr=log,
        text=True
    )
    log.write(f"\nReturn code: {result.returncode}\n")
    log.flush()
