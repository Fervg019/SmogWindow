"""Open the offline dashboard in your browser:  python demo.py   (builds it first if needed; no server, no network)."""
import webbrowser
from pathlib import Path
import build_dashboard

root = Path(__file__).resolve().parent
page = root / 'SmogWindow_dashboard.html'
if not page.exists():
    build_dashboard.build()
print('Opening', page)
webbrowser.open(page.as_uri())
