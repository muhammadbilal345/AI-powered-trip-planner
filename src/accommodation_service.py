import requests
from typing import List, Dict, Any

class AccommodationService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_host = "skyscanner80.p.rapidapi.com"

    def get_hotels(self, query: str, market: str = "US", locale: str = "en-US") -> List[Dict[str, Any]]:
        url = "https://skyscanner80.p.rapidapi.com/api/v1/hotels/auto-complete"
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host
        }
        querystring = {
            "query": query,
            "market": market,
            "locale": locale
        }

        try:
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            data = response.json()
            
            hotels = []

            for item in data.get('data', []):
                # Add the main entityName
                hotels.append(item.get('entityName'))
                
                # If there are POIs, add their entityNames as well
                pois = item.get('pois', [])
                if pois:
                    for poi in pois:
                        hotels.append(poi.get('entityName'))
            return hotels

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return []

