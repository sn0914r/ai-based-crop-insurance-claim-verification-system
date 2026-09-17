from typing import Dict, Any, Optional

class WeatherEngine:
    """
    Core Agronomic Weather Engine for disaster evaluation,
    continuous weather severity scoring (0-100%), and damage cause classification.
    """

    @staticmethod
    def calculate_weather_score(weather_data: Dict[str, Any]) -> float:
        """
        Computes continuous weather damage severity percentage (0-100%).
        """
        rainfall = float(weather_data.get("rainfall_mm", 0.0))
        temp_max = float(weather_data.get("temp_max", 30.0))
        wind_speed = float(weather_data.get("wind_speed", 15.0))
        dry_days = int(weather_data.get("consecutive_dry_days", 0))

        # 1. Rainfall / Flood severity
        flood_score = 0.0
        if rainfall >= 150.0:
            flood_score = 100.0
        elif rainfall >= 100.0:
            flood_score = 80.0 + ((rainfall - 100.0) / 50.0) * 20.0
        elif rainfall >= 50.0:
            flood_score = 50.0 + ((rainfall - 50.0) / 50.0) * 30.0
        elif rainfall >= 25.0:
            flood_score = 20.0 + ((rainfall - 25.0) / 25.0) * 30.0

        # 2. Drought / Heatwave severity
        drought_score = 0.0
        if dry_days >= 14 and temp_max >= 38.0:
            heat_excess = min(temp_max - 38.0, 10.0)
            drought_score = 70.0 + (heat_excess / 10.0) * 25.0
        elif dry_days >= 20 and temp_max >= 35.0:
            drought_score = 40.0 + min((dry_days - 20) * 1.5, 30.0)

        # 3. Storm / Wind lodging severity
        wind_score = 0.0
        if wind_speed >= 70.0:
            wind_score = 90.0
        elif wind_speed >= 55.0:
            wind_score = 50.0 + ((wind_speed - 55.0) / 15.0) * 35.0

        # Continuous meteorological severity is the peak hazard observed
        peak_score = max(flood_score, drought_score, wind_score)

        # Baseline mild weather noise
        if peak_score == 0.0:
            peak_score = min(rainfall * 0.5, 10.0)

        return round(min(peak_score, 100.0), 1)

    @classmethod
    def get_weather_hazard(cls, weather_data: Dict[str, Any]) -> str:
        """
        Identifies the meteorological hazard directly from weather metrics.
        """
        rainfall = float(weather_data.get("rainfall_mm", 0.0))
        temp_max = float(weather_data.get("temp_max", 30.0))
        wind_speed = float(weather_data.get("wind_speed", 15.0))
        dry_days = int(weather_data.get("consecutive_dry_days", 0))

        if rainfall >= 75.0:
            return "FLOOD"
        if (dry_days >= 14 and temp_max >= 38.0) or (dry_days >= 20 and temp_max >= 35.0):
            return "DROUGHT"
        if wind_speed >= 60.0:
            return "STORM_LODGING"
        return "NORMAL"

    @classmethod
    def evaluate_weather(cls, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates weather data and returns impact score, weather hazard, and structured metrics.
        """
        weather_score = cls.calculate_weather_score(weather_data)
        weather_hazard = cls.get_weather_hazard(weather_data)
        anomaly_detected = (weather_score >= 50.0)

        return {
            "weatherScore": weather_score,
            "weatherHazard": weather_hazard,
            "anomalyDetected": anomaly_detected,
            "metrics": {
                "rainfallMm": weather_data.get("rainfall_mm", 0.0),
                "tempMaxC": weather_data.get("temp_max", 30.0),
                "tempMinC": weather_data.get("temp_min", 20.0),
                "windSpeedKmh": weather_data.get("wind_speed", 15.0),
                "consecutiveDryDays": weather_data.get("consecutive_dry_days", 0)
            },
            "region": weather_data.get("region", "Farm Location"),
            "dataSource": weather_data.get("dataSource", "UNKNOWN")
        }

weather_engine = WeatherEngine()
