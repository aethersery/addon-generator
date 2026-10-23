import fastapi
import uvicorn
import pydantic

with open('/storage/emulated/0/Android/data/com.androidharness.app/files/workspace/test_deps.txt', 'w') as f:
    f.write(f"fastapi: {fastapi.__version__}\n")
    f.write(f"uvicorn: {uvicorn.__version__}\n")
    f.write(f"pydantic: {pydantic.__version__}\n")
