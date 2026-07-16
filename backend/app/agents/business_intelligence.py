import os
import json
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, List
from config import settings
from app.services.firestore_service import firestore_service

logger = logging.getLogger("saudagar_ai.agent.business_intelligence")

class BusinessIntelligenceAgent:
    def __init__(self):
        # Resolve path relative to this file so it works from any working directory
        _base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.festivals_file = os.path.join(_base, "data", "festivals.json")

    def run_update(self):
        """
        Runs the Business Intelligence collection workflow.
        Fetches weather, upcoming festivals, and trends, and updates Firestore.
        """
        logger.info("Running Business Intelligence Agent update...")
        
        weather = self._fetch_weather()
        festivals = self._get_upcoming_festivals()
        trends = self._fetch_google_trends(weather)

        insights_data = {
            "updated_at": datetime.utcnow().isoformat(),
            "weather": weather,
            "trends": trends,
            "festivals": festivals
        }

        firestore_service.update_business_insights(insights_data)
        logger.info("Successfully updated Business Insights in Firestore.")
        return insights_data

    def _fetch_weather(self) -> Dict[str, Any]:
        """
        Fetches current weather. Falls back to seasonal mock if API key is missing.
        """
        api_key = settings.OPENWEATHER_API_KEY
        city = "Mumbai"  # Default city representing Indian retail hub
        
        if api_key:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            try:
                response = httpx.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "city": city,
                        "temp": data["main"]["temp"],
                        "condition": data["weather"][0]["main"],
                        "humidity": data["main"]["humidity"],
                        "source": "OpenWeather API"
                    }
                else:
                    logger.error(f"Weather API returned status {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"Error calling Weather API: {e}")

        # Fallback Mock: Determine based on current month (July is rainy/monsoon in India)
        current_month = datetime.now().month
        if current_month in [6, 7, 8, 9]:
            temp = 29.0
            condition = "Rainy"
            humidity = 88
        elif current_month in [10, 11, 12, 1, 2]:
            temp = 22.0
            condition = "Cool"
            humidity = 55
        else:
            temp = 36.0
            condition = "Hot/Sunny"
            humidity = 60

        return {
            "city": city,
            "temp": temp,
            "condition": condition,
            "humidity": humidity,
            "source": "Seasonal Mock (No Key)"
        }

    def _get_upcoming_festivals(self) -> List[Dict[str, Any]]:
        """
        Reads festivals.json, calculates days remaining for each festival,
        and returns sorted list of upcoming ones.
        """
        upcoming = []
        if not os.path.exists(self.festivals_file):
            logger.warning(f"Festivals file not found at {self.festivals_file}. Returning empty list.")
            return upcoming

        try:
            with open(self.festivals_file, "r") as f:
                festivals_list = json.load(f)

            now = datetime.now()
            current_year = now.year

            for fest in festivals_list:
                # Parse approx date with current year (or next year if already passed)
                approx_str = fest["approx_date"]
                approx_date = datetime.strptime(approx_str, "%Y-%m-%d")
                
                # Adjust year to current or next year depending on date
                fest_date = datetime(year=current_year, month=approx_date.month, day=approx_date.day)
                if fest_date < now:
                    fest_date = datetime(year=current_year + 1, month=approx_date.month, day=approx_date.day)
                
                days_away = (fest_date - now).days
                
                upcoming.append({
                    "name": fest["name"],
                    "date": fest_date.strftime("%Y-%m-%d"),
                    "days_away": days_away,
                    "impact_categories": fest["impact_categories"],
                    "description": fest["description"]
                })
                
            # Sort by days_away
            upcoming.sort(key=lambda x: x["days_away"])
        except Exception as e:
            logger.error(f"Error parsing upcoming festivals: {e}")

        # Limit to top 2 upcoming festivals
        return upcoming[:2]

    def _fetch_google_trends(self, weather: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates search trend intelligence based on weather conditions.
        """
        condition = weather.get("condition", "").lower()
        
        # Base trends
        trends = {
            "packaged_foods": 50,
            "beverages": 50,
            "hygiene": 50,
            "confectionery": 50
        }

        # Dynamic search spikes based on weather
        if "rain" in condition or "cloud" in condition:
            trends["packaged_foods"] = 85  # Instant noodles, soup spike during rain
            trends["beverages"] = 65  # Hot tea/coffee search spikes
        elif "cool" in condition or "winter" in condition:
            trends["packaged_foods"] = 80
            trends["beverages"] = 75  # Tea/coffee up
        elif "hot" in condition or "sunny" in condition:
            trends["beverages"] = 90  # Ice creams, cold drinks spike
            trends["packaged_foods"] = 40

        return trends

business_intelligence_agent = BusinessIntelligenceAgent()
