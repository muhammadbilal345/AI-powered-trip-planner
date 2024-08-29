import requests
from typing import Dict, Any
from datetime import datetime

class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_forecast(self, location: str, date: str) -> Dict[str, Any]:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={self.api_key}&units=metric"
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()

        # Convert input date to datetime for comparison
        target_date_str = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')

        # Iterate over the forecast data to find the closest match to the target date
        for forecast in data['list']:
            forecast_date = forecast['dt_txt'].split(' ')[0]
            if forecast_date == target_date_str:
                weather_details = {
                    'date': forecast_date,
                    'location': location,
                    'temperature': forecast['main']['temp'],
                    'description': forecast['weather'][0]['description']
                }
                return weather_details

        # If no matching date is found, return an error message
        return {"error": f"No weather data available for {date} in {location}."}

