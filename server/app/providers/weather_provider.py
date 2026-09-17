import csv
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import urllib.request
import json

from app.configs.settings import SERVER_DIR

logger = logging.getLogger(__name__)

class WeatherProvider:
    """
    Hybrid weather provider combining local public weather dataset
    with dynamic open-access ERA5/NOAA historical weather API.
    """
    DATASET_FILE = SERVER_DIR / "data" / "weather_dataset.csv"

    @classmethod
    def _read_dataset_data(cls, limit: Optional[int] = None) -> list:
        records = []
        if cls.DATASET_FILE.exists():
            try:
                with open(cls.DATASET_FILE, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if limit is not None and i >= limit:
                            break
                        records.append(row)
            except Exception as e:
                logger.warning(f"Could not read weather dataset file: {str(e)}")
        return records

    @classmethod
    def _lookup_dataset(cls, latitude: float, longitude: float, incident_date: str) -> Optional[Dict[str, Any]]:
        """
        Looks up historical record in the consolidated 2,680-record public dataset.
        Matches on latitude and longitude (rounded to 1 decimal place) and incident date.
        """
        if not cls.DATASET_FILE.exists():
            return None

        lat_round = round(latitude, 1)
        lon_round = round(longitude, 1)
        target_date = incident_date.strip()

        try:
            with open(cls.DATASET_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        row_lat = round(float(row["latitude"]), 1)
                        row_lon = round(float(row["longitude"]), 1)
                        row_date = row.get("date", "").strip()

                        if row_lat == lat_round and row_lon == lon_round and row_date == target_date:
                            return {
                                "rainfall_mm": float(row["rainfall_mm"]),
                                "temp_max": float(row["temp_max"]),
                                "temp_min": float(row["temp_min"]),
                                "wind_speed": float(row.get("wind_speed_kmh", 15.0)),
                                "consecutive_dry_days": int(row.get("consecutive_dry_days", 0)),
                                "region": row.get("region", "Historical Region"),
                                "scenario": row.get("anomaly_type", "Historical Observation"),
                                "dataSource": "PUBLIC_DATASET_CSV"
                            }
                    except (ValueError, KeyError):
                        continue
        except Exception as e:
            logger.warning(f"Error reading weather dataset: {str(e)}")

        return None

    @classmethod
    def _query_live_api(cls, latitude: float, longitude: float, incident_date: str) -> Dict[str, Any]:
        """
        Queries Open-Meteo Historical Weather API for the 7-day window surrounding the date.
        """
        try:
            target_dt = datetime.strptime(incident_date.strip(), "%Y-%m-%d")
        except ValueError:
            target_dt = datetime.utcnow()

        start_date = (target_dt - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = (target_dt + timedelta(days=3)).strftime("%Y-%m-%d")

        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={latitude}&longitude={longitude}&"
            f"start_date={start_date}&end_date={end_date}&"
            f"daily=precipitation_sum,temperature_2m_max,temperature_2m_min,wind_gusts_10m_max&"
            f"timezone=auto"
        )

        req = urllib.request.Request(url, headers={"User-Agent": "CropInsuranceAI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))

        daily = data.get("daily", {})
        precip_list = daily.get("precipitation_sum", [0.0])
        temp_max_list = daily.get("temperature_2m_max", [30.0])
        temp_min_list = daily.get("temperature_2m_min", [22.0])
        wind_list = daily.get("wind_gusts_10m_max", [15.0])

        # Replace None values with safe defaults
        clean_precip = [p if p is not None else 0.0 for p in precip_list]
        clean_tmax = [t if t is not None else 30.0 for t in temp_max_list]
        clean_tmin = [t if t is not None else 22.0 for t in temp_min_list]
        clean_wind = [w if w is not None else 15.0 for w in wind_list]

        # Calculate consecutive dry days (rain < 1mm)
        dry_days = 0
        for p in reversed(clean_precip):
            if p < 1.0:
                dry_days += 1
            else:
                break

        return {
            "rainfall_mm": round(float(sum(clean_precip)), 1),
            "temp_max": round(float(max(clean_tmax)), 1),
            "temp_min": round(float(min(clean_tmin)), 1),
            "wind_speed": round(float(max(clean_wind)), 1),
            "consecutive_dry_days": dry_days,
            "region": f"GPS ({round(latitude, 2)}, {round(longitude, 2)})",
            "scenario": "Live Meteorological Archive",
            "dataSource": "LIVE_ERA5_API"
        }

    @classmethod
    def get_weather_data(cls, latitude: float, longitude: float, incident_date: str) -> Dict[str, Any]:
        """
        Hybrid retrieval: Checks local benchmark dataset first.
        If not found, queries live Open-Meteo ERA5 API.
        Falls back to nearest benchmark in case of network issues.
        """
        # 1. Check local public dataset CSV
        dataset_record = cls._lookup_dataset(latitude, longitude, incident_date)
        if dataset_record:
            return dataset_record

        # 2. Query Live Public API
        try:
            return cls._query_live_api(latitude, longitude, incident_date)
        except Exception as e:
            logger.warning(f"Live weather query failed ({str(e)}). Using offline fallback.")
            # Fallback: return default normal baseline
            return {
                "rainfall_mm": 5.0,
                "temp_max": 30.0,
                "temp_min": 22.0,
                "wind_speed": 18.0,
                "consecutive_dry_days": 3,
                "region": f"GPS ({round(latitude, 2)}, {round(longitude, 2)})",
                "scenario": "Offline Fallback Baseline",
                "dataSource": "OFFLINE_FALLBACK"
            }

weather_provider = WeatherProvider()
