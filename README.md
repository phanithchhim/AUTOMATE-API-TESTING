# Automated API Testing (pytest)

Template project for API testing using pytest and requests.

Quickstart (PowerShell):

```powershell
cd "e:\AHOLTP0575\Project ALL\CMSPORTAL-API\AUTOMATE-API-TESTING"
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q --html=report.html
```

Edit `config.yaml` to point to your API base URL and credentials. Update tests in `tests/` to match your endpoints.
