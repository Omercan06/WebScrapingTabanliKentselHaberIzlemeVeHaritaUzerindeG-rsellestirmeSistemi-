import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Env dosyasından URI al
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGO_DETAILS = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.kocaeli_news_db
news_collection = database.get_collection("news")

async def clear_database():
    print("Mevcut veri tabanı koleksiyonu ('news') siliniyor...")
    await news_collection.drop()
    print("Veri tabanı başarıyla temizlendi!")
    print("Şimdi backend'inizi tekrar başlatarak kazıma (scraping) yaptığınızda ")
    print("yeni E5 modeli tamamen temiz ve doğru verilerle sistemi baştan kuracaktır.")

if __name__ == "__main__":
    asyncio.run(clear_database())
