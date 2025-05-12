import os
from pathlib import Path
from datetime import datetime

# Base directory for saved articles
BASE_DIR = Path(__file__).resolve().parent
SAVED_ARTICLES_DIR = os.path.join(BASE_DIR, "saved_articles")

# Create the base directory if it doesn't exist
os.makedirs(SAVED_ARTICLES_DIR, exist_ok=True)

# API settings
MAX_RESULTS = 25

def get_today_folder():
    """Get the folder path for today's date in YYYYMMDD format"""
    today = datetime.now().strftime("%Y%m%d")
    folder_path = os.path.join(SAVED_ARTICLES_DIR, today)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path 