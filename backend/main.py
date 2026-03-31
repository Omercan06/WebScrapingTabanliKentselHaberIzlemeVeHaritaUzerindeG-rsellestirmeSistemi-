from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from backend.database import init_db, news_collection
from backend.scraper import run_scraper_pipeline

app = FastAPI(title="Kocaeli News Map API")

# Allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to Kocaeli News API"}

@app.get("/api/news")
async def get_news():
    # ZORUNLU İSTER: Sadece son 3 günün haberlerini göster (ISO 8601)
    three_days_ago_str = (datetime.now() - timedelta(days=3)).isoformat()
    cursor = news_collection.find({"date": {"$gte": three_days_ago_str}}, {"_id": 0})
    news_list = []
    async for document in cursor:
        news_list.append(document)
    return {"data": news_list}

@app.post("/api/scrape")
async def trigger_scrape():
    count = await run_scraper_pipeline()
    return {"message": f"Scraping triggered successfully. Added {count} new articles."}
