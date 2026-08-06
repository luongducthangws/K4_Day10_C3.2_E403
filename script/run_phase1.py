from pathlib import Path
import sys

# Ensure src/ is in sys.path
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from pipelines.phase1 import main


if __name__ == "__main__":
    main()
