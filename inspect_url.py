import requests

url = "http://stream.live.vc.bbcmedia.co.uk/bbc_radio_one"
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, stream=True, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    
    # Read first 100 bytes
    chunk = response.raw.read(100)
    print(f"First 100 bytes: {chunk}")
    
    response.close()
except Exception as e:
    print(f"Error: {e}")
