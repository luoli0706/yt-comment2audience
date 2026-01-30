# Image_Analyse (Flask)

## Run (Windows PowerShell)

```powershell
# This repo tracks `.venv` (without site-packages). If you don't have a working venv,
# create your own and install dependencies manually.
python -m venv .venv
\.\.venv\Scripts\Activate.ps1
# (Optional) install deps if you have requirements locally
# pip install -r requirements.txt
python app.py
```

Then open:
- http://127.0.0.1:5000/
- http://127.0.0.1:5000/health
