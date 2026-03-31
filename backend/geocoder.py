import os
import httpx
from backend.database import database
import urllib.parse
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Get the collection for caching coordinates
location_cache_collection = database.get_collection("location_cache")

async def get_coordinates(location_text):
    """
    Convert a location string into latitude and longitude coordinates.
    CRITICAL: Utilizes MongoDB caching to prevent duplicate API requests and save costs.
    """
    if not location_text:
        return None

    # 1. CHECK MONGODB CACHE FIRST
    # We normalize the text to ensure minor casing differences don't cause duplicate lookups
    normalized_location = location_text.lower().strip()
    
    cached_location = await location_cache_collection.find_one({"location_query": normalized_location})
    if cached_location:
        print(f"CACHE HIT: Found coordinates for '{location_text}' in MongoDB.")
        return {"lat": cached_location["lat"], "lng": cached_location["lng"]}

    # 2. IF NOT IN CACHE, CALL GOOGLE GEOCODING API
    print(f"CACHE MISS: Calling Google API for '{location_text}'...")
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("ERROR: Valid Google Maps API Key is required for Geocoding.")
        # DO NOT return fake coordinates if it fails; let it fail as per requirements ("Geocoding başarısız olursa kayıt işlenmemelidir.")
        return None

    encoded_location = urllib.parse.quote(location_text)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_location}&key={api_key}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            data = response.json()

            if data.get("status") == "OK" and len(data.get("results", [])) > 0:
                location = data["results"][0]["geometry"]["location"]
                lat = location["lat"]
                lng = location["lng"]
                
                # 3. SAVE TO MONGODB CACHE FOR FUTURE USE
                await location_cache_collection.insert_one({
                    "location_query": normalized_location,
                    "original_text": location_text,
                    "lat": lat,
                    "lng": lng
                })
                print(f"SAVED TO CACHE: '{location_text}' -> ({lat}, {lng})")
                
                return {"lat": lat, "lng": lng}
            else:
                print(f"Geocoding failed for '{location_text}': {data.get('status')} - {data.get('error_message', '')}")
                return None
    except Exception as e:
        print(f"Exception during geocoding '{location_text}': {e}")
        return None
