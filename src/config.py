import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

CITY_COORDINATES = {
    "Bengaluru": (12.9716, 77.5946),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Kolkata": (22.5726, 88.3639),
}

def settings():
    return {
        "api_key": os.getenv("XKDR_API_KEY", ""),
        "database_url": os.getenv("DATABASE_URL", "postgresql+psycopg2://airquality:airquality@localhost:5432/airquality"),
        "cities": [c.strip() for c in os.getenv("CITIES", "Bengaluru,Delhi,Mumbai").split(",") if c.strip()],
        "lookback_hours": int(os.getenv("LOOKBACK_HOURS", "168")),
    }
