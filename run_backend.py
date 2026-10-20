"""
Backend runner script for Company Lead Finder FastAPI server.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "backend"
for p in (root_dir, backend_dir):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
