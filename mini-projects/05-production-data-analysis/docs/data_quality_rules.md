# Mini Proje 5 — Veri Üretim, Hata Enjeksiyonu ve Veri Kalitesi (Temizlik) Kuralları

Bu belge, **AI-Based Smart Production Planning and Decision Support System** ana projesinin 5. adımı olan *Pandas ile Üretim Verisi Analizi* kapsamında kullanılan sentetik veri üretim kurallarını, kontrollü hata enjeksiyonu tasarımını ve veri temizleme (data cleaning) sözleşmesini açıklar.

> **Temel İlke:** Veri temizleme katmanı **sessiz düzeltme (silent correction) yapmaz**. Hatalı veya tahmine dayalı kayıtları koruyarak KPI'ları çarpıtmak yerine, belgelenmiş tek varsayılan atama dışında tüm bozuk/eksik kayıtlar tespit edilir, günlüğe (`cleaning_log`) kaydedilir ve veri setinden çıkarılır.

---

## 1. Ham Veri Üretimi ve Kontrollü Hata Enjeksiyonu Kuralları

### 1.1 Temiz Ham Veri Kaynağı (`raw_records_clean.csv`)
- **Üretim Yöntemi:** Mini Proje 4'ün vektörel simülasyon motoru (`SimulationConfig.from_factory` -> `simulate` -> `simulation_to_records`) ve Mini Proje 3'ün `RecordStore` yapısı kullanılarak üretilir.
- **Kapsam ve Boyut:** `sample_factory.json` içindeki aktif makineler (M1, M2, M3, M5) için 120 günlük (`2026-10-01` – `2027-01-28`) üretim simüle edilir.
  - M1, M3 ve M5 günde 1 vardiya (`morning`) -> $3 \times 120 = 360$ kayıt.
  - M2 günde 2 vardiya (`morning`, `afternoon`) -> $2 \times 120 = 240$ kayıt.
  - M4 (`maintenance` durumunda / uygun değil) simülasyonda üretim yapmaz -> $0$ kayıt.
  - **Toplam:** 600 temiz kayıt (`record_id` 1–600).
- **Tekrarlanabilirlik:** Rastgele sayı üreteci tohumu `seed=42` (`np.random.default_rng(42)`) ile sabitlenmiştir.

### 1.2 Kontrollü Hata Enjeksiyonu (`raw_records_dirty.csv` / `.json`)
Gerçek sahada (MES / ERP entegrasyonlarında, operatör veri girişlerinde veya sensör kopmalarında) karşılaşılan veri kalitesi sorunlarını deterministik biçimde test edebilmek için 600 temiz kayıt üzerine `seed=42` ile kontrollü hatalar enjekte edilir:

1. **Tekil Satır Hataları (66 Satır):**
   `rng.choice(600, size=66, replace=False)` ile tekrarsız 66 satır seçilir ve aşağıdaki `FAULT_PLAN` sırasıyla ardışık dilimlere bölünerek **her satıra yalnızca bir hata** uygulanır:

| Hata Türü (`fault_type`) | Adet | Uygulanan Bozulma | Gerçek Hayat Karşılığı ve Nedeni |
| :--- | :---: | :--- | :--- |
| `missing_actual_units` | 12 | `actual_units` -> `<NA>` (boş) | Vardiya sonunda operatörün üretim sayısını girmeyi unutması veya sayaç verisinin gelmemesi. |
| `missing_downtime_hours` | 12 | `downtime_hours` -> `<NA>` (boş) | Duruş yaşanmayan vardiyalarda operatörün `0.0` yazmak yerine alanı boş bırakması. |
| `negative_actual_units` | 6 | `actual_units` -> `-(actual_units + 1)` | Hurda/iade düşümü sırasında oluşan işaret hatası veya yanlış veri girişi. |
| `non_numeric_actual_units` | 6 | `actual_units` -> `"abc"` | Sayısal alana metin/açıklama yazılması veya bozuk CSV/JSON serileştirmesi. |
| `downtime_too_high` | 6 | `downtime_hours` -> `9.5` | 8 saatlik vardiyada 8 saatten fazla duruş girilmesi (birim karışıklığı veya günlük toplamın vardiyaya yazılması). |
| `invalid_shift` | 6 | `shift` -> `"evening"` | Standart vardiya sözlüğü (`morning`, `afternoon`, `night`) dışında etiket kullanımı. |
| `unknown_machine_id` | 6 | `machine_id` -> `"M9"` | Fabrika ana tablosunda (`machine_master`) tanımlı olmayan makine kodu. |
| `invalid_date` | 6 | `production_date` -> `"2026-13-40"` | Takvimde var olmayan tarih veya bozuk tarih dizgesi. |
| `zero_planned_units` | 6 | `planned_units` -> `0` | Planlanan üretimin 0 girilmesi (üretim planı olmayan kaydın gerçekleşme oranı hesaplanamaz; sıfıra bölme hatası yaratır). |

2. **Çift Kayıt / Mükerrer Gönderim (`duplicate_key`, 10 Satır):**
   Bozulmayan 534 satır arasından `rng.choice(remaining, size=10, replace=False)` ile 10 satır seçilir ve aynı `(production_date, shift, machine_id)` anahtarına sahip kopyaları yeni `record_id` (`601`–`610`) ile tablonun sonuna eklenir.
   - **Neden:** Ağ gecikmesi veya formun iki kez gönderilmesi sonucu aynı makine ve vardiyanın sisteme mükerrer kaydedilmesini temsil eder.

3. **Toplam Kirli Veri Seti:**
   - Kirli veri: $600 + 10 = 610$ satır.
   - Enjeksiyon günlüğü (`fault_injection_log.csv`): $66 + 10 = 76$ satır.

---

## 2. Veri Yükleme ve Tür Sözleşmesi

### 2.1 Neden Ham Veri Metin (`string`) Olarak Yüklenir?
`load_records_dataframe()` fonksiyonu CSV ve JSON dosyalarını doğrudan sayısal/tarih türlerine çevirmeden, tüm sütunları Pandas `"string"` veri tipinde yükler:
- **Eksik (`<NA>`) ile Geçersiz (`"abc"`) Ayrımı:** Eğer yükleme sırasında otomatik tür dönüşümü (`errors='coerce'`) yapılsaydı, boş bırakılan `actual_units` ile `"abc"` yazılan `actual_units` aynı anda `NaN`/`<NA>` değerine dönüşecek ve `missing_actual_units` ile `invalid_actual_units` birbirinden ayırt edilemeyecekti.
- **Boşluk Karakterleri:** Yalnızca boşluktan oluşan hücreler (`"   "`) yükleme ve temizliğin ilk adımında `<NA>` kabul edilir; ancak `" Morning"` veya `" M1"` gibi bozuk değerler sessizce kırpılmaz (`strip` edilmez), kural ihlali olarak yakalanır.

---

## 3. Veri Temizleme Kuralları ve İşlem Sırası (`clean_records`)

`clean_records(raw_df, machine_master, product_master)` fonksiyonu, Mini Proje 3'ün veri doğrulama kurallarını birebir koruyarak aşağıdaki **5 adımlı kesin sırayı** vektörel boolean maskelerle uygular:

### Adım 1: Boş / Yalnızca Boşluk İçeren Hücrelerin Normalize Edilmesi
- Boş dizgeler (`""`) ve yalnızca boşluk karakterlerinden oluşan dizgeler (`"   "`) `<NA>` olarak işaretlenir.
- Dolu hücrelerin içeriğine dokunulmaz.

### Adım 2: Tür Dönüşümü (`errors='coerce'`) ve Sorun İşaretleme (Issue Flagging)
Her kural için vektörel bir boolean maske üretilir. **Önemli kural:** Bir alan eksikse (`<NA>`) yalnızca ilgili `missing_*` kodu üretilir; aynı alan için ayrıca `invalid_*` veya `unknown_*` kodu üretilmez. Bir satırda **farklı alanlarda** birden fazla hata varsa, her hata temizlik günlüğüne (`cleaning_log_df`) ayrı bir satır olarak yazılır.

| Sıra | `issue` Kodu | Koşul (Tespit Kuralı) | İşlem (`action`) | Kuralın Gerekçesi (Neden?) |
| :---: | :--- | :--- | :---: | :--- |
| 1 | `missing_key_field` | `production_date`, `shift`, `machine_id`, `product_code` veya `planned_units` alanlarından en az biri `<NA>` | `dropped` | Kaydın hangi gün, vardiya, makine veya ürüne ait olduğu ya da hedef üretimi bilinmiyorsa kayıt analizde kullanılamaz. |
| 2 | `missing_actual_units` | `actual_units` alanı `<NA>` | `dropped` | Gerçekleşen üretim miktarı olmadan üretim açığı, gerçekleşme oranı ve kapasite kullanımı hesaplanamaz; tahminle doldurma KPI'ları bozar. |
| 3 | `missing_downtime_hours` | `downtime_hours` alanı `<NA>` | `filled` (`0.0`) | MP3 veri sözleşmesinde `downtime_hours` varsayılan olarak `0.0` saattir. Operatör duruş olmadığında alanı boş bırakabildiği için tek güvenli ve belgelenmiş doldurma kuralı budur. |
| 4 | `invalid_date` | `production_date` dolu olduğu halde sıkı ISO `YYYY-MM-DD` biçiminde değil veya geçerli bir takvim tarihi değil (ör. `2026-02-30`, `01.10.2026`, `2026-13-40`) | `dropped` | Zaman serisi, günlük/haftalık toplulaştırma ve sıralama işlemlerinin hatasız çalışması için geçerli takvim tarihi zorunludur. |
| 5 | `invalid_shift` | `shift` dolu olduğu halde `{'morning', 'afternoon', 'night'}` kümesinde değil | `dropped` | Vardiya bazlı KPI karşılaştırmalarında tanımsız vardiya grupları oluşmasını engeller. |
| 6 | `unknown_machine_id` | `machine_id` dolu olduğu halde `machine_master` tablosunda yok | `dropped` | Ana tabloda karşılığı olmayan makinenin hat bilgisi ve vardiya efektif kapasitesi (`shift_effective_capacity`) bilinemez. (*Not:* Makinenin `is_available=False` olması temizlikte hata sayılmaz; ana tabloda bulunması yeterlidir.) |
| 7 | `unknown_product_code` | `product_code` dolu olduğu halde `product_master` tablosunda yok | `dropped` | Ana tabloda karşılığı olmayan ürünün çevrim süresi ve öncelik (`priority`) bilgisi bilinemez. |
| 8 | `invalid_planned_units` | `planned_units` dolu olduğu halde sayıya dönüşemiyor, $\le 0$ veya tam sayı değerli değil (`800.0` kabul, `800.5` ret) | `dropped` | Adet bazlı üretimde yarım adet planlanamaz ve $\le 0$ plan, gerçekleşme oranı (`actual / planned`) formülünde sıfıra bölme veya anlamsız yüzde üretir. |
| 9 | `invalid_actual_units` | `actual_units` dolu olduğu halde sayıya dönüşemiyor, $< 0$ veya tam sayı değerli değil (`0` kabul) | `dropped` | Üretim miktarı negatif veya kesirli adet olamaz. (`0` adet üretim ise tüm vardiyanın duruşta geçtiği geçerli bir senaryodur.) |
| 10 | `invalid_downtime_hours` | `downtime_hours` dolu olduğu halde sayıya dönüşemiyor, $< 0$ veya $> 8.0$ (`8.0` kabul, `8.01` ret) | `dropped` | Bir vardiya 8 saattir (`SHIFT_HOURS = 8.0`). Negatif duruş veya vardiya süresini aşan duruş fiziksel olarak imkânsızdır ve kullanılabilirlik (`availability_pct`) hesabını bozar. |
| 11 | `duplicate_key` | Adım 3 sonrası kalan geçerli satırlarda aynı `(production_date, shift, machine_id)` anahtarına sahip birden fazla kayıt varsa, **en küçük `record_id` dışındaki** kayıtlar | `dropped` | Bir makine aynı gün ve vardiyada yalnızca tek bir vardiya özet kaydına sahip olabilir (MP3 benzersizlik kuralı). İlk oluşturulan kayıt (`min(record_id)`) asıl kayıt kabul edilir, sonraki kopyalar silinir. |

### Adım 3: Silinecek (`dropped`) Satırların Çıkarılması
- Adım 2'de `dropped` eylemine sahip herhangi bir sorunu bulunan satırlar veri çerçevesinden çıkarılır.
- Bir satırda birden fazla `dropped` hatası varsa (örneğin hem `invalid_shift` hem `invalid_actual_units`), günlükte iki ayrı satır yer alır ancak satır yalnızca **bir kez** silinir (`dropped_row_count` benzersiz `record_id` üzerinden sayılır).

### Adım 4: Eksik `downtime_hours` Değerlerinin Doldurulması (`0.0`)
- Adım 3'ü geçen satırlarda `<NA>` olan `downtime_hours` değerleri `0.0` ile doldurulur.
- Eğer bir satır başka bir hatadan dolayı Adım 3'te silinmişse ve aynı zamanda `missing_downtime_hours` içeriyorsa, sorun günlüğe kaydedilir fakat o satır temiz veriye dahil edilmez (`filled_row_count` yalnızca temiz veride kalan doldurulmuş satırları sayar).

### Adım 5: Mükerrer Anahtarların (`duplicate_key`) Temizlenmesi ve Son Biçimlendirme
- Kalan satırlar `record_id` artan sıraya dizilir.
- `(production_date, shift, machine_id)` üçlüsü üzerinde `duplicated(keep='first')` kontrolü yapılarak en küçük `record_id` korunur; daha büyük `record_id`'li kopyalar `duplicate_key` olarak günlüğe eklenir ve silinir.
- Çıktı `clean_df`, Bölüm 3.2'deki kesin veri tiplerine (`int64`, `datetime64`, `string`, `float64`) dönüştürülür, `record_id` sırasına göre sıralanır ve indeksi `0..n-1` olarak sıfırlanır.

---

## 4. Altın Değer Özeti (610 Satırlık Kirli Veri Seti Üzerinde)

| Metrik | Değer | Açıklama |
| :--- | :---: | :--- |
| Ham veri satır sayısı (`raw_row_count`) | **610** | 600 orijinal + 10 kopya satır |
| Temiz veri satır sayısı (`clean_row_count`) | **546** | Tüm MP3 doğrulamalarından geçen temiz kayıtlar |
| Silinen satır sayısı (`dropped_row_count`) | **64** | 54 hatalı satır + 10 mükerrer (`duplicate_key`) satır |
| Doldurulan satır sayısı (`filled_row_count`) | **12** | `missing_downtime_hours` -> `0.0` yapılan satırlar |
| Temizlik günlüğü satır sayısı (`len(cleaning_log_df)`) | **76** | 64 silinen + 12 doldurulan sorun kaydı |
