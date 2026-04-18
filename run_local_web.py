from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(ROOT / ".env")

os.environ.setdefault("HEXMIND_PERSONAS_DIR", str(ROOT / "personas"))
os.environ.setdefault("HEXMIND_PROMPTS_DIR", str(ROOT / "prompts" / "library"))
os.environ.setdefault("HEXMIND_ARCHIVE_DIR", str(ROOT / "discussion_archive"))

frontend_dist = ROOT / "web" / "dist"
if frontend_dist.exists():
    os.environ.setdefault("HEXMIND_WEB_DIST_DIR", str(frontend_dist))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HexMind local web app on a single local port.",
    )
    parser.add_argument("--host", default=os.getenv("HEXMIND_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("HEXMIND_PORT", "8000")),
    )
    args = parser.parse_args()

    print(f"HexMind local app: http://{args.host}:{args.port}")
    uvicorn.run(
        "hexmind.api.app:app",
        host=args.host,
        port=args.port,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    main()
