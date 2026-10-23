import subprocess
import sys

with open('/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/pip_minimal.log', 'w') as log:
    log.write("Starting minimal pip install...\n")
    log.flush()
    
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-r', '/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/requirements_minimal.txt'],
        stdout=log,
        stderr=log,
        text=True
    )
    log.write(f"\nReturn code: {result.returncode}\n")
    log.flush()
