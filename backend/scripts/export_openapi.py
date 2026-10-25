"""Export the FastAPI OpenAPI schema to the repository docs directory."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

repo_root = Path(__file__).resolve().parents[2]
output_path = repo_root / "docs" / "openapi.json"
output_path.write_text(
    json.dumps(app.openapi(), indent=2) + "\n",
    encoding="utf-8",
)
print(output_path)
