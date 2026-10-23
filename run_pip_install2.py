import subprocess
import sys

with open('/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/pip_install2.log', 'w') as log:
    log.write("Starting pip install with --only-binary...\n")
    log.flush()
    
    # Try with --only-binary for pydantic-core
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--only-binary=:all:', 'fastapi', 'pydantic', 'pydantic-settings', 'python-dotenv', 'httpx'],
        stdout=log,
        stderr=log,
        text=True
    )
    log.write(f"\nReturn code: {result.returncode}\n")
    log.flush()
