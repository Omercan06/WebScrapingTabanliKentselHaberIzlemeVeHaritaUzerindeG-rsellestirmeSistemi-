from huggingface_hub import snapshot_download

print("E5 Modeli internetten indiriliyor... Bu işlem boyut ve internet hızınıza göre vakit alabilir.")
print("Lütfen aşağıdaki progress bar (yüzdelik çubuğu) %100 olana kadar bekleyin.\n")

# İndirme işlemi için Hugging Face fonksiyonunu kullanıyoruz (çubuğu göstermeyi zorlar)
snapshot_download(repo_id="intfloat/multilingual-e5-base")

print("\n\n✅ Model başarıyla bilgisayarınıza indirildi ve kuruldu!")
print("Artık test_e5.py dosyasını veya ana backend'i çalıştırabilirsiniz.")
