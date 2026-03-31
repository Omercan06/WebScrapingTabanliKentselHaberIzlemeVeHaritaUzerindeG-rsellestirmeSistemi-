import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Change to your remote MongoDB URI if you are using Atlas
MONGO_DETAILS = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.kocaeli_news_db
news_collection = database.get_collection("news")

async def init_db():
    # Zorunlu İster: MongoDB Schema Validasyonu
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["type", "title", "content", "locationText", "lat", "lng", "date", "sourceName", "url"],
            "properties": {
                "type": { "bsonType": "string", "description": "Haber türü (Zorunlu)" },
                "title": { "bsonType": "string", "description": "Başlık (Zorunlu)" },
                "content": { "bsonType": "string", "description": "İçerik (Zorunlu)" },
                "locationText": { "bsonType": "string", "description": "Konum metni (Zorunlu)" },
                "lat": { "bsonType": "double", "description": "Enlem koordinatı (Zorunlu)" },
                "lng": { "bsonType": "double", "description": "Boylam koordinatı (Zorunlu)" },
                "date": { "bsonType": "string", "description": "Yayın tarihi - ISO 8601 (Zorunlu)" },
                "sourceName": { "bsonType": "string", "description": "Site adı (Zorunlu)" },
                "url": { "bsonType": "string", "description": "Orijinal link (Zorunlu)" },
                "sources": { "bsonType": "array", "description": "Tüm duplicate kaynaklar listesi" }
            }
        }
    }
    
    try:
        # Koleksiyon varsa Schema'yı güncelle
        await database.command("collMod", "news", validator=validator)
    except Exception:
        # Koleksiyon yoksa Schema ile oluştur
        try:
            await database.create_collection("news", validator=validator)
        except Exception as e:
            print("Collection error (might already exist without mod support):", e)
            
    # URL tekrarını önlemek için Unique Index
    await news_collection.create_index("url", unique=True)
    print("Database connected, schema validated and indexes ensured.")
