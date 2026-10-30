# CSV ve JSON Dosya Biçimleri Karşılaştırması

Bu doküman, Mini Proje 3 kapsamında üretim kayıtlarının kalıcı olarak saklanmasında kullanılan **CSV** ve **JSON** dosya biçimlerinin teknik özelliklerini, avantaj/dezavantajlarını ve **1000 kayıtlık gerçek veri kümesi üzerinde yapılan boyut ve performans ölçümlerini** içerir.

---

## 1. Ölçüm Ortamı ve Yöntemi

Ölçümler, projedeki gerçek `ProductionRecord`, `storage.py` ve `record_store.py` modülleri kullanılarak gerçekleştirilmiştir:

- **Veri Kümesi:** `data/sample_factory.json` fabrika modeli üzerinden `generate_records(factory, "2026-01-01", days=200, seed=42)` ile üretilen **1000 adet** geçerli `ProductionRecord` kaydı (200 gün × günde 5 vardiya kaydı).
- **Ortam:** Python 3.12.0, Windows, standart kütüphane (`csv`, `json`, `os.replace`), UTF-8 kodlama.
- **Yöntem:** Tekil işlem süreleri `time.perf_counter()` ile 20 tekrar üzerinden medyan (ortanca) alınarak; ardışık ekleme testi ise boş dosyadan başlayarak 1000 kaydın tek tek eklenmesiyle ölçülmüştür.

---

## 2. 1000 Kayıtlık Performans ve Boyut Ölçüm Sonuçları

| Ölçülen Metrik (1000 Kayıt) | CSV (`.csv`) | JSON (`.json`, `indent=2`) | Oran / Karşılaştırma |
| :--- | :--- | :--- | :--- |
| **Dosya Boyutu (1000 kayıt)** | **43.518 bayt** (42,50 KB) | **250.469 bayt** (244,60 KB) | JSON **5,76 kat** daha büyük |
| **Kayıt Başına Ortalama Boyut** | **43,5 bayt / kayıt** | **250,5 bayt / kayıt** | CSV %82,6 daha az yer kaplar |
| **Toplu Yazma (`save_records_*`, 1000 kayıt)** | **3,74 ms** | **11,36 ms** | CSV **3,04 kat** daha hızlı |
| **Toplu Okuma (`load_records_*`, 1000 kayıt)** | **5,70 ms** | **5,01 ms** | JSON ~%12 daha hızlı (C tabanlı ayrıştırıcı + hazır tipler) |
| **1000 Kayıtlık Dosyaya Tek Kayıt Ekleme (`append_record_*`)** | **0,864 ms** | **25,602 ms** | CSV **29,6 kat** daha hızlı (`'a'` kipi vs oku-değiştir-yaz) |
| **`RecordStore.add_record` (1000 kayıt + doğrulama + ekleme)** | **15,53 ms** | **31,90 ms** | CSV **2,05 kat** daha hızlı |
| **Boş Dosyaya 1000 Ardışık Tekil Ekleme (Toplam Süre)** | **815,8 ms** (0,82 sn) | **19.175,3 ms** (19,18 sn) | CSV **23,5 kat** daha hızlı ($O(N)$ vs $O(N^2)$) |

> **Ek Boyut Notu (150 Kayıtlık Örnek Veri):** Projede teslim edilen 30 günlük (150 kayıtlık) `data/sample_records.csv` dosyası **6.513 bayt (6,36 KB)** iken, aynı veriyi içeren `data/sample_records.json` dosyası **37.512 bayt (36,63 KB)** boyutundadır (5,76 kat fark).

---

## 3. Karşılaştırma Tablosu (Ölçümlerle Doğrulanmış)

Aşağıdaki tablo, proje planı Bölüm 5.1'deki karşılaştırma iskeletinin 1000 kayıtlık gerçek test ve ölçüm sonuçlarıyla doğrulanmış halidir:

| Ölçüt | CSV | JSON |
| :--- | :--- | :--- |
| **Ekleme** | Dosya sonuna `'a'` kipinde tek satır eklenir, mevcut veriye dokunulmaz (**1000 kayıtlık dosyada tek ekleme: 0,864 ms; 1000 ardışık ekleme: 0,82 sn – $O(1)$ ekleme**). | Dosyanın tamamı okunur, listeye eklenir ve yeniden yazılır (**1000 kayıtlık dosyada tek ekleme: 25,602 ms; 1000 ardışık ekleme: 19,18 sn – her eklemede $O(N)$, toplamda $O(N^2)$ maliyet**). |
| **Yazma sırasında hata riski** | Doğrudan dosya sonuna yazıldığı için kesinti anında yarım kalan son satır riski taşır. | Atomik yazımla (`path + '.tmp'` geçici dosyasına yazıp `os.replace` ile değiştirme) kesintilere karşı tam korunur; eski dosya bozulmaz. |
| **Veri türleri** | Her alan metin (`str`) olarak saklanır; okurken `int` ve `float` dönüşümü gerekir (toplu okumada tip dönüşümü nedeniyle **5,70 ms**). | Sayı (`int`, `float`), metin (`str`) ve mantıksal (`bool`/`null`) değer ayrımı doğal olarak korunur (toplu okumada **5,01 ms**). |
| **İç içe veri** | Düz tablo (satır/sütun) yapısındadır; hiyerarşik veya iç içe veri için uygun değildir. | Üst düzey meta veri (`{"schema_version": 1, "records": [...]}`) ve iç içe nesne/listeleri doğal olarak destekler. |
| **Excel / Pandas uyumu** | Excel'de doğrudan tablo olarak açılır, `pandas.read_csv()` ile tek satırda yüklenir. | `pandas.json_normalize()` veya `records` anahtarından yükleme gerektirir; Excel'de doğrudan açmak için dönüştürme gerekir. |
| **Boyut** | Başlık satırı yalnızca bir kez yazıldığı için çok daha küçüktür (**1000 kayıtta 43.518 bayt / 42,50 KB; ~43,5 bayt/kayıt**). | Her kayıtta 8 alan adı (`record_id`, `production_date`, vb.) ve girintiler tekrarlandığı için **5,76 kat** daha büyüktür (**1000 kayıtta 250.469 bayt / 244,60 KB; ~250,5 bayt/kayıt**). |
| **Şema değişikliği** | Sabit sütun sırasına bağlıdır; yeni sütun eklenmesi veya sıranın değişmesi eski dosyaların başlık doğrulamasını bozar. | `schema_version` alanı ve anahtar-değer yapısı sayesinde yeni alanlar varsayılan değerlerle geriye dönük uyumlu biçimde eklenebilir. |

---

## 4. Değerlendirme ve Kullanım Önerileri

1. **Günlük Vardiya Kaydı Ekleme ve Tablo Paylaşımı İçin CSV:**
   - Düşük dosya boyutu (%82,6 tasarruf), $O(1)$ dosya sonuna ekleme hızı (**0,864 ms**) ve üretim mühendislerinin Excel ile doğrudan inceleyebilmesi nedeniyle varsayılan kayıt biçimi (`data/records.csv`) olarak **CSV** tercih edilmiştir.
   - Durumsuz `RecordStore.add_record` kullanıldığında dahi (mükerrer anahtar kontrolü için önce okuma yapıldığından) CSV, JSON'a kıyasla **2 kat daha hızlı** (**15,53 ms** vs **31,90 ms**) çalışmaktadır.

2. **Veri Bütünlüğü, Şema Evrimi ve Sistemler Arası Entegrasyon İçin JSON:**
   - Atomik yazma (`tmp` + `os.replace`) sayesinde elektrik/sistem kesintilerinde dosya bozulma riskini ortadan kaldırır.
   - `schema_version` desteği ve veri tiplerini koruması nedeniyle fabrika yapılandırması (`data/sample_factory.json`) ve API/servis alışverişlerinde **JSON** daha güvenlidir.
   - Kayıt sayısı büyüdüğünde JSON ile tek tek `append_record_json` çağırmak yerine `RecordStore.add_records` ile toplu yazma (**11,36 ms / 1000 kayıt**) kullanılmalıdır.

3. **İlişkisel Veritabanına Geçiş (Mini Proje 9 Bağlantısı):**
   - Her iki dosya biçiminde de `RecordStore` mükerrerlik kontrolü (`get_key()`) ve filtreleme için dosyayı baştan okumaktadır. Kayıt sayısı on binlere ulaştığında indeksli arama, ACID işlemleri ve eşzamanlı erişim için Mini Proje 9'da `RecordStore` arayüzü korunarak ilişkisel veritabanına (SQLite/PostgreSQL) geçilecektir.
