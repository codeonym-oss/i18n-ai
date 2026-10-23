from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LANGUAGE_CODE = "en"
USE_I18N = True
LOCALE_PATHS = [BASE_DIR / "locale"]
