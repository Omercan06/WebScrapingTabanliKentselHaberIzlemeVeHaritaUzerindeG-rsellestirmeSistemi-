import os
import httpx
import bs4
import warnings
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
import re
from datetime import datetime, timedelta
import asyncio
from bson import ObjectId

from backend.database import news_collection
from backend.nlp_processor import clean_html, classify_news, extract_location, calculate_embeddings, check_semantic_duplicate
from backend.geocoder import get_coordinates
import numpy as np

# Define the local news sources
SOURCES = [
    {"name": "Çağdaş Kocaeli", "url": "https://www.cagdaskocaeli.com.tr/"},
    {"name": "Özgür Kocaeli", "url": "https://www.ozgurkocaeli.com.tr/"},
    {"name": "Ses Kocaeli", "url": "https://www.seskocaeli.com/"},
    {"name": "Yeni Kocaeli", "url": "https://www.yenikocaeli.com/"},
    {"name": "Bizim Yaka", "url": "https://www.bizimyaka.com/"}
]

async def scrape_site(client, source, three_days_ago):
    """
    Generalized scraping function adapted to fetch from the specific Kocaeli news sites. 
    It focuses on getting lists of news URLs and then parsing each article for its content and date.
    """
    print(f"Scraping started for: {source['name']}")
    scraped_articles = []
    
    try:
        # 1. Fetch main page to find article links
        response = await client.get(source['url'], timeout=15.0, follow_redirects=True)
        soup = bs4.BeautifulSoup(response.text, 'html.parser')
        
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Simple heuristic: news articles usually have longer paths or IDs
            if 'haber' in href or len(href) > 35:
                if href.startswith('/'):
                    href = source['url'].rstrip('/') + href
                
                if href.startswith(source['url']):
                     links.add(href)
                     
        # Haber hacmini artırmak için limitleri 40'tan 100'e çıkarıyoruz
        links = list(links)[:100] 
        print(f"Found {len(links)} potential article links for {source['name']}")
        
        for link in links:
            # Quick duplicate check to skip already processed URLs
            existing = await news_collection.find_one({"sources.url": link})
            if existing:
                continue
                
            # 2. Fetch article page
            try:
                article_response = await client.get(link, timeout=10.0, follow_redirects=True)
                article_soup = bs4.BeautifulSoup(article_response.text, 'html.parser')
            except Exception as e:
                print(f"Failed to fetch {link}: {e}")
                continue
            
            # Extract Title
            title_tag = article_soup.find('h1')
            title = title_tag.text.strip() if title_tag else ""
            if not title:
                continue # Skip if no title found
            
            # Extract Content (finding largest text block)
            paragraphs = article_soup.find_all('p')
            raw_html_content = " ".join([p.text for p in paragraphs if len(p.text) > 20])
            
            clean_text = clean_html(raw_html_content)
            if not clean_text or len(clean_text) < 50:
                continue # Skip very short/empty articles
                
            # Extract Date
            publish_date = None # No more "now()" fallback to ensure accuracy
            date_str = None
            
            # 1. Try to grab date from meta tags (Modern CMS)
            date_meta = article_soup.find('meta', property='article:published_time') or article_soup.find('meta', itemprop='datePublished')
            if date_meta and date_meta.get('content'):
                date_str = date_meta['content']
                
            # 2. Try JSON-LD (Extremely reliable for Google News compliant sites)
            if not date_str:
                ld_json = article_soup.find('script', type='application/ld+json')
                if ld_json and ld_json.string:
                    import json
                    try:
                        data = json.loads(ld_json.string)
                        if isinstance(data, list): data = data[0]
                        if '@graph' in data:
                            for item in data['@graph']:
                                if item.get('datePublished'):
                                    date_str = item.get('datePublished')
                                    break
                        elif data.get('datePublished'):
                            date_str = data.get('datePublished')
                    except Exception:
                        pass

            # 3. Try HTML5 <time> elements
            if not date_str:
                time_tag = article_soup.find('time')
                if time_tag and time_tag.get('datetime'):
                    date_str = time_tag['datetime']
                elif time_tag:
                    date_str = time_tag.text

            # 4. Try to find Visual Date Spans by CSS patterns
            if not date_str:
                date_span = article_soup.find(class_=re.compile(r'tarih|date|published', re.I))
                if date_span:
                    date_str = date_span.text

            # Robust Parsing Logic for Turkish and Universal Formats
            if date_str:
                date_str_clean = date_str.strip()
                try:
                    if 'T' in date_str_clean and len(date_str_clean) > 10: # ISO Format Handling
                        iso_str = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', date_str_clean)
                        if iso_str:
                            publish_date = datetime.fromisoformat(iso_str.group(0))
                    elif re.fullmatch(r'\d{2}:\d{2}', date_str_clean): 
                        # Eğer siteden sadece saat geliyorsa (17:28 vb.), bu bugünün haberidir.
                        h, m = map(int, date_str_clean.split(':'))
                        publish_date = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
                    else: 
                        # 1. Numeric formats (e.g. 11/03/2026)
                        date_match = re.search(r'(\d{1,2})[\./-](\d{1,2})[\./-](\d{4})', date_str_clean)
                        if date_match:
                            day, month, year = map(int, date_match.groups())
                            publish_date = datetime(year, month, day, 12, 0)
                        else:
                            # 2. Textual formats (e.g. 13 Mart 2026, 30 MAR 2026, 30 MAR)
                            tr_months = ["ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım", "aralık"]
                            en_short = {"jan":1, "feb":2, "mar":3, "apr":4, "may":5, "jun":6, "jul":7, "aug":8, "sep":9, "oct":10, "nov":11, "dec":12}
                            
                            lower_date = date_str_clean.lower()
                            
                            month_num = None
                            for abbr, m_num in en_short.items():
                                if abbr in lower_date:
                                    month_num = m_num
                                    break
                                    
                            if not month_num:
                                for i, month_name in enumerate(tr_months):
                                    if month_name in lower_date:
                                        month_num = i + 1
                                        break
                                        
                            if month_num:
                                day_match = re.search(r'\b(\d{1,2})\b', lower_date)
                                year_match = re.search(r'\b(\d{4})\b', lower_date)
                                
                                if day_match:
                                    day = int(day_match.group(1))
                                    year = int(year_match.group(1)) if year_match else datetime.now().year
                                    publish_date = datetime(year, month_num, day, 12, 0)
                except Exception:
                    pass
            
            # ZORUNLU İSTER: Son 3 günlük zaman dilimine göre veri çekmelidir.
            if not publish_date:
                print(f"DEBUG: Dropped (No valid date parsed). Title: {title} | raw date_str: {date_str}")
                # If date couldn't be parsed, skip to avoid old news "bleeding" in
                continue

            # Convert to naive datetime for comparison
            naive_publish = publish_date.replace(tzinfo=None) if publish_date.tzinfo else publish_date
            
            if naive_publish < three_days_ago:
                print(f"DEBUG: Dropped (Older than 3 days). Title: {title} | Parsed: {naive_publish.isoformat()}")
                continue 
                
            # ZORUNLU İSTER: Tarihleri ISO 8601 formatına çevirerek MongoDB'ye kaydet
            formatted_date_str = naive_publish.isoformat()
            
            scraped_articles.append({
                "title": title,
                "content": clean_text,
                "url": link,
                "date": formatted_date_str,
                "sourceName": source['name']
            })
            
    except Exception as e:
        print(f"Error scraping {source['name']}: {e}")
        
    return scraped_articles

async def process_articles(articles):
    """
    Runs the scraped articles through the NLP and Geocoding pipeline.
    """
    processed_count = 0
    updated_count = 0
    
    # Pre-fetch recent articles from DB for similarity checking
    # Fetching only last 30 days to keep memory low. (We match using our new string-based date format)
    three_days_ago_db_str = (datetime.now() - timedelta(days=30)).isoformat()
    cursor = news_collection.find({"date": {"$gte": three_days_ago_db_str}})
    
    existing_news_docs = []
    texts_to_encode = []
    
    async for doc in cursor:
        combined_text = doc["title"] + " " + doc["content"]
        existing_news_docs.append({
            "id": str(doc["_id"]),
            "url": doc.get("url"),
            "sources": doc.get("sources", [])
        })
        texts_to_encode.append(combined_text)
        
    # Calculate all existing embeddings in a single batch (High Performance)
    existing_embeddings = calculate_embeddings(texts_to_encode)
    existing_ids = [doc["id"] for doc in existing_news_docs]
    
    for article in articles:
        # EXACT MATCH CHECK: "Aynı haber birden fazla kez kaydedilmemelidir"
        # If url already exists exactly inside existing db docs or batch, perfectly match and skip.
        if any(article['url'] == ex.get('url') for ex in existing_news_docs):
            continue
            
        # 1. Classify
        category = classify_news(article['content'], article['title'])
        if not category:
             continue
             
        # 2. Check for semantic duplicates (Cosine Similarity >= %90)
        combined_text = article['title'] + " " + article['content']
        is_dup, dup_id = await check_semantic_duplicate(combined_text, existing_embeddings, existing_ids)
        
        if is_dup:
            print(f"DUPLICATE DETECTED (Similarity >= 90%). Merging sources for: {article['title']}")
            
            target_doc_index = existing_ids.index(dup_id)
            target_doc = existing_news_docs[target_doc_index]
            target_source_urls = [s.get('url') for s in target_doc.get('sources', [])]
            
            if article['url'] not in target_source_urls:
                new_source = {
                    "name": article['sourceName'],
                    "url": article['url']
                }
                try:
                    await news_collection.update_one(
                        {"_id": ObjectId(dup_id)},
                        {"$addToSet": {"sources": new_source}} 
                    )
                    target_doc['sources'].append(new_source)
                    updated_count += 1
                except Exception as e:
                    print(f"Failed to update duplicate doc {dup_id}: {e}")
            continue
            
        # 3. Extract Location
        location_text = extract_location(article['content'])
        if not location_text:
            print(f"No location found. Skipping: [{category}] {article['title']}")
            continue
            
        # 4. Geocode Location (With Cache!)
        coords = await get_coordinates(location_text)
        if not coords:
            print(f"Geocoding failed for '{location_text}'. Skipping: {article['title']}")
            continue
            
        # 5. Save to DB
        news_doc = {
            "title": article['title'],
            "content": article['content'],
            "date": article['date'],
            "type": category,
            "locationText": location_text,
            "lat": coords['lat'],
            "lng": coords['lng'],
            "url": article['url'],
            "sourceName": article['sourceName'],
            # Store sources in an array to support multiple sources
            "sources": [
                {
                    "name": article['sourceName'],
                    "url": article['url']
                }
            ]
        }
        
        try:
            result = await news_collection.insert_one(news_doc)
            if result.inserted_id:
                processed_count += 1
                print(f"Successfully processed and saved: [{category}] {article['title']}")
            
            # Maintain embeddings array dynamically for subsequent loop items
            new_doc_id_str = str(result.inserted_id)
            existing_news_docs.append({
                "id": new_doc_id_str,
                "url": article['url'],
                "sources": news_doc["sources"]
            })
            existing_ids.append(new_doc_id_str)
            
            from backend.nlp_processor import similarity_model
            if similarity_model:
                new_embed = similarity_model.encode([combined_text])
                if existing_embeddings is None or len(existing_embeddings) == 0:
                    existing_embeddings = new_embed
                else:
                    existing_embeddings = np.vstack([existing_embeddings, new_embed])
                    
        except Exception as e:
            print(f"DB Insert error handling {article['title']}: {e}")
            
    return processed_count, updated_count

async def run_scraper_pipeline():
    """
    Main orchestrator for scraping.
    """
    print("--- Scraping Pipeline Started ---")
    start_time = datetime.now()
    
    # Zaman filtresi: test için 30 gündü, proje zorunlu isteri gereği 'son 3 gün' olarak düzeltildi.
    three_days_ago = start_time - timedelta(days=3)
    three_days_ago_str = three_days_ago.isoformat()
    
    # 0. DATABASE CLEANUP: ZORUNLU İSTER (Son 3 gün dışındakileri sil)
    # Temizliği yeni standart Tarih String'ine göre yapıyoruz.
    # Güvenlik amaçlı: Eski tip "datetime" date objelerini doğrudan DB'den siliyoruz.
    await news_collection.delete_many({"date": {"$type": "date"}})
    delete_result = await news_collection.delete_many({"date": {"$lt": three_days_ago_str}})
    if delete_result.deleted_count > 0:
        print(f"CLEANUP: Removed {delete_result.deleted_count} news articles older than 3 days.")
    
    all_scraped_articles = []
    
    async with httpx.AsyncClient(verify=False) as client:
        # Run scrapers concurrently
        tasks = [scrape_site(client, source, three_days_ago) for source in SOURCES]
        results = await asyncio.gather(*tasks)
        
        for res in results:
            all_scraped_articles.extend(res)
            
    print(f"Total raw articles scraped from 5 sources: {len(all_scraped_articles)}")
    
    # Process through pipeline
    processed_count, updated_count = await process_articles(all_scraped_articles)
    
    duration = datetime.now() - start_time
    print(f"--- Scraping Pipeline Completed in {duration} ---")
    print(f"Successfully saved {processed_count} new articles and merged {updated_count} duplicates.")
    
    return processed_count + updated_count

if __name__ == "__main__":
    # To test locally
    try:
        asyncio.run(run_scraper_pipeline())
    except Exception as e:
        import traceback
        print("Fatal error in scraper pipeline:")
        traceback.print_exc()
