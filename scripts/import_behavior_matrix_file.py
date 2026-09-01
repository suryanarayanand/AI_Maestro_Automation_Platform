import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.services.behavior_matrix_service import import_behavior_matrix


if len(sys.argv) != 2:
    raise SystemExit("Usage: import_behavior_matrix_file.py <matrix.xlsx>")

result = import_behavior_matrix(Path(sys.argv[1]))
print(result)
