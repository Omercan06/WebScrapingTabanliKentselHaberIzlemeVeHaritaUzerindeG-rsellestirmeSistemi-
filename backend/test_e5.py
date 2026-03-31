import asyncio
from nlp_processor import classify_news

def test():
    # Test 1: Obvious accident
    title = "Körfez'de feci trafik kazası"
    text = "Körfez ilçesinde iki otomobilin çarpışması sonucu meydana gelen zincirleme trafik kazasında 3 kişi yaralandı. Olay yerine ambulans ve polis ekipleri sevk edildi. Araçlar hurdaya döndü."
    print("Test 1 (Trafik Kazası):", classify_news(text, title))
    
    # Test 2: AI dominant example (ambiguous words but clear meaning)
    title = "Elektrikler kesilince mahalle karanlığa gömüldü"
    text = "Dün gece yaşanan fırtına nedeniyle direk devrildi ve bölgedeki tüm evlerin enerjisi kesildi. Vatandaşlar yetkililerden yardım bekliyor."
    print("Test 2 (Elektrik Kesintisi):", classify_news(text, title))
    
    # Test 3: Negative example
    title = "Kocaelispor'dan muhteşem idman"
    text = "Takımımız bugün yaptığı çalışma ile pazar günkü zorlu deplasman maçı öncesi hazırlıklarını tamamladı. Şampiyonluk parolasıyla sahaya çıkacağız."
    print("Test 3 (None - Spor):", classify_news(text, title))

if __name__ == "__main__":
    test()
