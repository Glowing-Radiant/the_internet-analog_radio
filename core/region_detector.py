import requests

class RegionDetector:
    def __init__(self):
        self.api_url = "http://ip-api.com/json/"

    def get_region(self):
        try:
            response = requests.get("http://ip-api.com/json/", timeout=5)
            data = response.json()
            return {
                'countryCode': data.get('countryCode', 'US'),
                'city': data.get('city', ''),
                'lat': data.get('lat', 0.0),
                'lon': data.get('lon', 0.0)
            }
        except Exception as e:
            print(f"Error detecting region: {e}")
            return {'countryCode': 'US', 'city': '', 'lat': 0.0, 'lon': 0.0}
