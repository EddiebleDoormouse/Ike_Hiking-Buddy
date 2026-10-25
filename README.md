# Ike_Hiking-Buddy
Helping hand for all your hiking needs :)

## Run the backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp ../.env.example ../.env
# Fill in any API keys or connection strings needed for your setup.
uvicorn app.main:app --reload
python -m pytest -q
python scripts/export_openapi.py
python scripts/smoke_gemini.py
```
