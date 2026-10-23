import subprocess
import sys

with open('/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/pip_install3.log', 'w') as log:
    log.write("Starting pip install from requirements...\n")
    log.flush()
    
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--only-binary=:all:', '-r', '/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/requirements_simple.txt'],
        stdout=log,
        stderr=log,
        text=True
    )
    log.write(f"\nReturn code: {result.returncode}\n")
    log.flush()
