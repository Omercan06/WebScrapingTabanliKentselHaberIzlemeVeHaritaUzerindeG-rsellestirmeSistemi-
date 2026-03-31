import os
import torch
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

# Fix: Load .env from its actual location (backend/.env)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Detect GPU availability
device = 0 if torch.cuda.is_available() else -1
print(f"DEBUG: NLP Processor using device: {'GPU' if device == 0 else 'CPU'}")

# We load "intfloat/multilingual-e5-base" as it supports Turkish exceptionally well.
try:
    similarity_model = SentenceTransformer('intfloat/multilingual-e5-base', device='cuda' if device == 0 else 'cpu')
except Exception as e:
    print("Warning: Could not load E5-base model. AI classification will be disabled.", e)
    similarity_model = None

# Defining our target categories for the LLM as per documentation
TARGET_CATEGORIES = [
    "Trafik Kazası", 
    "Yangın", 
    "Elektrik Kesintisi", 
    "Hırsızlık", 
    "Kültürel Etkinlikler"
]

# Hedef ve Gürültü (Noise) Önermeleri (Zıtlıklarla Doğru Sınıflandırma İçin)
ALL_PROMPTS = {
    # 5 GERÇEK HEDEF KATEGORİ
    "Trafik Kazası": "passage: Trafik kazası, araçların ve otomobillerin çarpışması, zincirleme kaza, kamyonun takla atması, yayaya çarpma veya şarampole yuvarlanma haberi.",
    "Yangın": "passage: İtfaiye ekiplerinin müdahale ettiği ev, konut, iş yeri, çatı veya orman yangını, kundaklama ile doğalgaz patlaması haberi.",
    "Hırsızlık": "passage: Evden veya işyerinden hırsızlık, maskeli hırsızların kasayı çalması, soygun, nitelikli dolandırıcılık, gasp ve kapkaç olayı haberi.",
    "Elektrik Kesintisi": "passage: SEDAŞ tarafından duyurulan planlı elektrik kesintisi, trafo patlaması, mahallenin karanlıkta kalması ve arıza kaynaklı enerji kopması haberi.",
    "Kültürel Etkinlikler": "passage: Kocaeli'de düzenlenen tiyatro gösterisi, canlı müzik, konser, kitap fuarı açılışı, sanatsal festival, söyleşi ve etkinlik haberi.",
    
    # KARIŞMAYI ÖNLEYİCİ GÜRÜLTÜ KATEGORİLERİ (Bunlara benzerse model direk çöpe atar)
    "NOISE_Siyaset": "passage: Siyaset, parti liderlerinin açıklamaları, belediye başkanı ziyareti, yerel seçimler, sandık sonuçları veya milletvekili demeci haberi.",
    "NOISE_Spor": "passage: Futbol takımı antrenmanı, maç sonuçları, spor kulübü transferleri, şampiyonluk maçı, Kocaelispor veya deplasman karşılaşması haberi.",
    "NOISE_Doga": "passage: Meteoroloji tahminleri, şiddetli kar yağışı, sağanak yağmur uyarısı, sel baskını, fırtına veya hortum gibi genel doğa olayları haberi.",
    "NOISE_Ekonomi": "passage: Belediye ihaleleri, araç ve mekan kiralama, asgari ücret zammı, altın, döviz fiyatları, borsa, ekonomik yatırımlar veya mali enflasyon haberi.",
    "NOISE_Cinayet_Ve_Asayis": "passage: Husumetli grupların silahlı kavgası, cinayet, adam öldürme olayı, bıçaklı saldırı, kurşunlama, uyuşturucu operasyonu veya silahla intihar vakası haberi.",
    "NOISE_Belediye_Hizmet": "passage: Belediye başkanının yol yapım çalışmaları, otopark ücretleri, asfalt ve temizlik yapımı, altyapı iyileştirme veya zabıta denetimi haberi.",
    "NOISE_Diger": "passage: Günlük sıradan yaşam olayları, okul haberleri, dinlenme tesisi, vefat ilanları, cenaze detayları, teknoloji duyuruları veya kampanya reklamı."
}

CATEGORY_KEYS = list(ALL_PROMPTS.keys())
CATEGORY_PASSAGES = list(ALL_PROMPTS.values())

# Pre-compute Category Embeddings
if similarity_model:
    print("DEBUG: Pre-computing E5 category embeddings for Target + Noise...")
    CATEGORY_EMBEDDINGS = similarity_model.encode(CATEGORY_PASSAGES, convert_to_tensor=False)
else:
    CATEGORY_EMBEDDINGS = None

KOCAELI_DISTRICTS = [
    "İzmit", "Gebze", "Gölcük", "Körfez", "Derince", 
    "Kartepe", "Darıca", "Çayırova", "Karamürsel", 
    "Dilovası", "Başiskele", "Kandıra"
]

def clean_html(html_str):
    if not html_str:
        return ""
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in soup(['script', 'style', 'meta', 'noscript', 'header', 'footer', 'aside', 'nav', 'iframe', 'button', 'form']):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.,!?\'"():;/%-]', '', text) 
    return text.strip()

def classify_news(text, title):
    text_lower = text.lower()
    title_lower = title.lower()
    
    # 1. TEMEL NEGATİF LİSTE (Sadece süreci hızlandırmak için sporu/ekonomiyi vb. keser)
    basic_negatives = [
        "idman", "kocaelispor", "süper lig", "amatör küme", "başkan adayı", "parti binası",
        "borsa", "kripto", "cenaze ilanları", "seri ilanlar", "vefat edenler"
    ]
    if any(k in title_lower for k in basic_negatives):
        return None

    # Model Kullanarak Yapay Zeka Zıtlık (Rekabetçi) Sınıflandırması
    if similarity_model is None or CATEGORY_EMBEDDINGS is None:
        return None

    # E5 "query:" öneki gerektirir ve içerik kısmını tarar
    news_query = f"query: {title}. {text_lower[:750]}"
    query_embedding = similarity_model.encode([news_query], convert_to_tensor=False)
    sims_array = cosine_similarity(query_embedding, CATEGORY_EMBEDDINGS)[0]
    
    best_idx = sims_array.argmax()
    best_score = sims_array[best_idx]
    best_category = CATEGORY_KEYS[best_idx]
    
    # Eğer model bu haberin en çok bir NOISE (Gürültü/Hedef Dışı) kategorisine uyduğuna karar verdiyse Reddet!
    # Örneğin: Uyuşturucu operasyonunu Hırsızlığa benzetmek yerine Cinayet/Asayiş gürültüsüne daha çok benzetip eleyecektir.
    if best_category.startswith("NOISE_"):
        return None
        
    # Eğer en yüksek skor bizim gerçek 5 hedef kategorimizden biriyse (Trafik, Yangın vb.):
    # Anlamsal yakınlığı %74 ve üzerinde olması bizim için ideal ve geniş bir doğrulamadır.
    if best_score >= 0.74:
        return best_category
        
    return None

def extract_location(text):
    if not text:
        return None
    specific_location = None
    location_regex = r'((?:[A-ZÇĞİÖŞÜ][a-zçğıöşü]*\s*){1,3}(?:Mahallesi|Mah\.|Sokak|Sok\.|Caddesi|Cad\.|Mevkii|Sapağı|Bulvarı))'
    match = re.search(location_regex, text)
    if match:
        specific_location = match.group(1).strip()
    district_found = None
    for district in KOCAELI_DISTRICTS:
        if re.search(r'\b' + district + r'\b', text, re.IGNORECASE):
            district_found = district
            break
    if specific_location and district_found:
        return f"{specific_location}, {district_found}, Kocaeli"
    elif specific_location:
        return f"{specific_location}, Kocaeli"
    elif district_found:
        return f"{district_found}, Kocaeli"
    return None

def calculate_embeddings(text_list):
    if not similarity_model or not text_list:
        return []
    processed_texts = [f"passage: {t}" for t in text_list]
    return similarity_model.encode(processed_texts)

async def check_semantic_duplicate(new_text, existing_embeddings, existing_ids, threshold=0.90):
    if not similarity_model or not new_text or existing_embeddings is None or len(existing_embeddings) == 0:
        return False, None
    query_text = f"query: {new_text}"
    new_embedding = similarity_model.encode([query_text])
    similarities = cosine_similarity(new_embedding, existing_embeddings)[0]
    for idx, sim in enumerate(similarities):
        if sim >= threshold:
            return True, existing_ids[idx]
    return False, None
