import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# When packaged with PyInstaller (--onefile), __file__ resolves inside a
# temporary extraction folder that's wiped on exit -- data/.env must live
# next to the actual .exe instead, so it survives between runs.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

DATA_DIR = APP_DIR / "data"

load_dotenv(APP_DIR / ".env")

HOSTEDSMS_EMAIL = os.getenv("HOSTEDSMS_EMAIL", "").strip()
HOSTEDSMS_PASSWORD = os.getenv("HOSTEDSMS_PASSWORD", "").strip()
HOSTEDSMS_SENDER = os.getenv("HOSTEDSMS_SENDER", "").strip()
