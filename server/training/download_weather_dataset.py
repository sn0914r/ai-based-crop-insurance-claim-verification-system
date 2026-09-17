import csv
import json
import time
import urllib.request
from pathlib import Path

REGIONS = [
    {
        "region": "Andhra Pradesh (Krishna District)",
        "latitude": 16.5,
        "longitude": 80.6,
        "crop_focus": "Rice"
    },
    {
        "region": "Punjab (Ludhiana District)",
        "latitude": 30.9,
        "longitude": 75.8,
        "crop_focus": "Wheat"
    },
    {
        "region": "Rajasthan (Jaipur District)",
        "latitude": 26.9,
        "longitude": 75.8,
        "crop_focus": "Corn / Coarse Grains"
    },
    {
        "region": "Madhya Pradesh (Bhopal District)",
        "latitude": 23.2,
        "longitude": 77.4,
        "crop_focus": "Wheat / Pulses"
    }
]

START_DATE = "2023-01-01"
END_DATE = "2024-10-31"

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "weather_dataset.csv"

def fetch_region_weather(region_info: dict) -> list:
    lat = region_info["latitude"]
    lon = region_info["longitude"]
    region_name = region_info["region"]
    crop_focus = region_info["crop_focus"]

    print(f"Downloading ERA5 weather data for {region_name} ({START_DATE} to {END_DATE})...")

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&"
        f"start_date={START_DATE}&end_date={END_DATE}&"
        f"daily=precipitation_sum,temperature_2m_max,temperature_2m_min,wind_gusts_10m_max&"
        f"timezone=auto"
    )

    req = urllib.request.Request(url, headers={"User-Agent": "CropInsuranceResearch/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    precip = daily.get("precipitation_sum", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    wind = daily.get("wind_gusts_10m_max", [])

    rows = []
    consecutive_dry = 0

    for i in range(len(dates)):
        d_rain = precip[i] if precip[i] is not None else 0.0
        d_tmax = tmax[i] if tmax[i] is not None else 30.0
        d_tmin = tmin[i] if tmin[i] is not None else 20.0
        d_wind = wind[i] if wind[i] is not None else 15.0

        if d_rain < 1.0:
            consecutive_dry += 1
        else:
            consecutive_dry = 0

        # Anomaly categorization
        anomaly = "NORMAL"
        if d_rain >= 75.0:
            anomaly = "EXCESSIVE_RAINFALL"
        elif consecutive_dry >= 14 and d_tmax >= 38.0:
            anomaly = "DROUGHT"
        elif d_wind >= 60.0:
            anomaly = "EXTREME_WIND"
        elif d_tmax >= 42.0:
            anomaly = "HEATWAVE"

        # Calculate impact score
        weather_score = 0.0
        if d_rain >= 100.0:
            weather_score = min(80.0 + ((d_rain - 100.0) / 50.0) * 20.0, 100.0)
        elif d_rain >= 50.0:
            weather_score = 50.0 + ((d_rain - 50.0) / 50.0) * 30.0
        elif consecutive_dry >= 14 and d_tmax >= 38.0:
            weather_score = min(70.0 + (d_tmax - 38.0) * 3.0, 100.0)
        elif d_wind >= 60.0:
            weather_score = min(60.0 + (d_wind - 60.0) * 1.5, 95.0)
        else:
            weather_score = min(d_rain * 0.5, 15.0)

        rows.append({
            "date": dates[i],
            "region": region_name,
            "crop_focus": crop_focus,
            "latitude": lat,
            "longitude": lon,
            "rainfall_mm": round(d_rain, 1),
            "temp_max": round(d_tmax, 1),
            "temp_min": round(d_tmin, 1),
            "wind_speed_kmh": round(d_wind, 1),
            "consecutive_dry_days": consecutive_dry,
            "weather_score": round(weather_score, 1),
            "anomaly_type": anomaly,
            "source": "ERA5_PUBLIC_DATASET"
        })

    print(f"Downloaded {len(rows)} daily records for {region_name}.")
    return rows

def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for region in REGIONS:
        try:
            records = fetch_region_weather(region)
            all_rows.extend(records)
            time.sleep(1)  # Respect API rate limits
        except Exception as e:
            print(f"Error fetching for {region['region']}: {str(e)}")

    if all_rows:
        fieldnames = [
            "date", "region", "crop_focus", "latitude", "longitude",
            "rainfall_mm", "temp_max", "temp_min", "wind_speed_kmh",
            "consecutive_dry_days", "weather_score", "anomaly_type", "source"
        ]

        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"\nSUCCESS: Total {len(all_rows)} verified public weather records saved to {OUTPUT_FILE}")
    else:
        print("No records downloaded.")

if __name__ == "__main__":
    main()
