import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    INPUT_DIR = os.getenv("INPUT_DIR", "/data/input")
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/data/output")
    ABS_URL = os.getenv("ABS_URL", "http://localhost:8080")
    ABS_API_KEY = os.getenv("ABS_API_KEY", "")
    STABILITY_CHECK_DURATION = int(os.getenv("STABILITY_CHECK_DURATION", "60"))
    ALLOWED_EXTENSIONS = {'.m4b', '.mp3', '.m4a', '.flac', '.opus', '.wma', '.epub', '.pdf', '.jpg', '.png'}
    # Thresholds for fuzzy matching
    MATCH_THRESHOLD_AUTOMATIC = 90
    MATCH_THRESHOLD_PROBABLE = 70
    
    # Permissions
    PUID = int(os.getenv("PUID", "1000"))
    PGID = int(os.getenv("PGID", "1000"))

    # Operations
    DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

    # Metadata providers
    METADATA_PROVIDERS = os.getenv("METADATA_PROVIDERS", "openlibrary,googlebooks,audible").split(",")
    
    # Web UI
    WEB_UI_ENABLED = os.getenv("WEB_UI_ENABLED", "true").lower() == "true"
    WEB_PORT = int(os.getenv("WEB_PORT", "3000"))
    API_PORT = int(os.getenv("API_PORT", "8000"))

    # Conversion
    CONVERT_TO_M4B = os.getenv("CONVERT_TO_M4B", "true").lower() == "true"
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg") 
    FFMPEG_HW_ACCEL = os.getenv("FFMPEG_HW_ACCEL", "auto") # auto, aac_at, cuda, none
    AUDNEXUS_URL = os.getenv("AUDNEXUS_URL", "https://api.audnexus.com")

config = Config()
