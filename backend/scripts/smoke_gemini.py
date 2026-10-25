"""Print a JSON smoke-test report for both Gemini models."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.gemini import ping_models

print(json.dumps(ping_models(), indent=2))
