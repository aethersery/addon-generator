import uvicorn
import sys
with open('/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/test_output.txt', 'w') as f:
    f.write("uvicorn version: " + uvicorn.__version__ + "\n")
    f.write("uvicorn file: " + uvicorn.__file__ + "\n")
    f.write("python: " + sys.version + "\n")
