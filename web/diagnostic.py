
import os
import sys

print("Checking dependencies...")
try:
    import docx
    print("SUCCESS: python-docx is installed.")
except ImportError:
    print("ERROR: python-docx is NOT installed.")

try:
    import PyPDF2
    print("SUCCESS: PyPDF2 is installed.")
except ImportError:
    print("ERROR: PyPDF2 is NOT installed.")

print("\nChecking dictionary file...")
# Path logic from __init__.py
from pathlib import Path
APP_DIR = Path(os.getcwd()) / "main_app" # Assuming running from web dir
WEB_DIR = Path(os.getcwd())
V2_DIR = WEB_DIR.parent
TSV_DICT_PATH = V2_DIR / "tsv-data" / "merge_lt_dict_v3.tsv"

print(f"Looking for dictionary at: {TSV_DICT_PATH}")
if TSV_DICT_PATH.exists():
    print("SUCCESS: Dictionary file exists.")
else:
    print("ERROR: Dictionary file NOT found.")
    # Try alternate location
    alt_path = Path("c:/Visual_studio/intern/v2/tsv-data/merge_lt_dict_v3.tsv")
    if alt_path.exists():
        print(f"SUCCESS: Found at absolute path: {alt_path}")
    else:
        print("ERROR: Dictionary file not found at absolute path either.")
