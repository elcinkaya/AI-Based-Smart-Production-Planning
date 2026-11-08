# Mini Proje 5: Pandas ile Üretim Verisi Analizi

**AI-Based Smart Production Planning and Decision Support System** (23 Mini Proje Yol Haritası – Sprint 1, Mini Proje 5)

Bu proje, Mini Proje 4'ün vektörel kapasite simülasyonu ve Mini Proje 3'ün kayıt depolama katmanıyla üretilen **600 satırlık** sentetik üretim verisine kontrollü veri kalitesi hataları (**610 satır**) enjekte eder; veriyi **Pandas** ile yükler, eksik ve hatalı kayıtları tespit edip temizler (**546 temiz satır**), türetilmiş değişkenleri ve eksiksiz günlük/haftalık zaman serilerini oluşturur, makine/ürün/vardiya/gün/hafta bazında KPI tablolarını hesaplar ve **yedi işletme sorusunu** gerçek veriler üzerinden yanıtlar.

---

## 1. Amaç ve Kapsam

- **Ham ve kirli veri üretim hattı:** MP4 `simulate` + `simulation_to_records` ve MP3 `RecordStore` ile 4 makine × 120 gün = **600 kayıt** üretilir; `np.random.default_rng(42)` ile 66 bozuk satır ve 10 kopya satır eklenerek **610 satırlık** kirli CSV/JSON veri seti oluşturulur.
- **Vektörel veri temizliği:** Tüm sütunlar önce `"string"` dtype olarak okunur; eksik (`<NA>`) ve geçersiz değerler 11 standart `issue` koduyla tespit edilip `cleaning_log.csv` dosyasına kaydedilir. Yalnızca eksik `downtime_hours` değerleri `0.0` ile doldurulur; hatalı ve mükerrer kayıtlar elenerek **546 temiz kayıt** elde edilir.
- **Türetilmiş değişkenler ve zaman serileri:** Makine ve ürün ana tabloları (`shift_effective_capacity`, `line_id`, `priority`) birleştirilir; `production_gap`, `attainment_pct`, `availability_pct`, `capacity_utilization_pct`, `plan_met`, `has_downtime`, `weekday`, `week_start` sütunları ile eksiksiz günlük seri (`freq='D'`, 7 günlük hareketli ortalama `actual_units_ma7`) ve Pazartesi başlangıçlı haftalık özet üretilir.
- **Grup bazlı KPI tabloları ve işletme soruları:** `groupby(...).agg(...)` ile grup toplamları üzerinden makine, ürün, vardiya, gün ve hafta KPI tabloları hesaplanır (`ddof=0`); yedi işletme sorusu (`q1`–`q7`) sabit değer kullanılmadan yanıtlanır.

---

## 2. Kurulum ve Çalıştırma

### Gereksinimler
- Python **3.10+** (referans ortam: **Python 3.12.0**)
- `numpy==2.4.4`
- `pandas==3.0.2`

### Kurulum
```bash
cd mini-projects/05-production-data-analysis
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### Konsol Uygulamasını Çalıştırma
```bash
python main.py
```
Uygulama menüsü (seçimler MP1 `get_number` ile doğrulanır):
1. Ham veri setini üret (MP4 + MP3 ile 600 kayıt, ardından hatalı sürüm)
2. Veriyi yükle ve temizle (temizlik özeti ve günlük)
3. KPI tablolarını göster (makine, ürün, vardiya, gün, hafta)
4. İşletme sorularını yanıtla
5. Analiz dosyalarını kaydet (`data/*.csv`)
6. Tüm hattı çalıştır (`1 → 5`) ve raporu yazdır
7. Çıkış

### Testleri Çalıştırma
```bash
python -m unittest discover tests -v
```

---

## 3. Varsayımlar ve Önceki Mini Projelerle Uyum

- **MP1 & MP2 (`factory_model`):** Makine teorik/efektif kapasiteleri yeni formül yazılmadan MP4 vektörel fonksiyonlarıyla (`calculate_theoretical_capacity_array`, `calculate_effective_capacity_array`) hesaplanır. Vardiya süresi `SHIFT_HOURS = 8.0` saattir; `shift_count = max(1, round(working_hours / 8))` ve `shift_effective_capacity = effective_capacity / shift_count` (`M1: 816, M2: 576, M3: 336, M4: 1710, M5: 768`).
- **MP3 (`production_records`):** Veri doğrulama kuralları, KPI formülleri, özet sözlüğü anahtarları ve Türkçe durum mesajları MP3 ile birebir aynıdır. Genel özet bloğu doğrudan MP3 `build_summary_report` fonksiyonuyla üretilir. `clean_records.csv` dosyası MP3 `RecordStore` ile doğrudan okunabilir.
- **MP4 (`capacity_simulation`):** Popülasyon standart sapması kuralı (`ddof=0`) tüm Pandas `.std(ddof=0)` çağrılarında açıkça uygulanır. Satır bazlı Python döngüsü, `iterrows`, `itertuples` ve `apply(axis=1)` kullanılmaz (yalnızca `loading.py` içindeki MP3 sınır dönüşümleri istisnadır).
- **Yuvarlama:** Hesaplamalarda ve CSV çıktılarında yuvarlama yapılmaz; yuvarlama yalnızca `report.py` içinde görüntüleme aşamasındadır.

---

## 4. Veri Üretim, Hata Enjeksiyonu ve Temizlik Kuralları

### 4.1 Kontrollü Hata Enjeksiyonu (`seed=42`, 600 → 610 satır)
600 temiz kayıttan `default_rng(42)` ile 66 satır seçilip aşağıdaki 9 hata türü uygulanır; kalan satırlardan 10 tanesi `record_id` `601–610` ile sona kopyalanır (toplam 76 hata günlüğü satırı):
- `missing_actual_units` (12), `missing_downtime_hours` (12)
- `negative_actual_units` (6), `non_numeric_actual_units` (`"abc"`, 6), `downtime_too_high` (`9.5`, 6)
- `invalid_shift` (`"evening"`, 6), `unknown_machine_id` (`"M9"`, 6), `invalid_date` (`"2026-13-40"`, 6), `zero_planned_units` (`0`, 6)
- `duplicate_key` (10 kopya satır, `record_id` 601–610)

### 4.2 5 Adımlı Temizlik Sırası (`clean_records`, 610 → 546 satır)
1. Boş veya yalnızca boşluk içeren hücreler `<NA>` yapılır.
2. Tür dönüşümleri (`errors='coerce'`) ve 10 doğrulama maskesi çalıştırılır (`missing_key_field`, `missing_actual_units`, `missing_downtime_hours`, `invalid_date`, `invalid_shift`, `unknown_machine_id`, `unknown_product_code`, `invalid_planned_units`, `invalid_actual_units`, `invalid_downtime_hours`).
3. `'dropped'` eylemli sorunu olan satırlar silinir (**54 satır**).
4. Kalan satırlarda eksik `downtime_hours` değerleri `0.0` ile doldurulur (**12 satır**, tek belgelenmiş düzeltme).
5. Kalan satırlarda `(production_date, shift, machine_id)` tekrarı olanların en küçük `record_id`'lisi korunur, diğerleri `duplicate_key` olarak silinir (**10 satır**).

Ayrıntılı kurallar için bkz. [`docs/data_quality_rules.md`](docs/data_quality_rules.md).

---

## 5. Tam Hat KPI Sonuçları (546 Temiz Kayıt)

- **Kapsam:** `546` kayıt (`2026-10-01` – `2027-01-28`, 120 gün, 18 hafta / 16 tam hafta)
- **Planlanan üretim:** `293032` adet
- **Gerçekleşen üretim:** `270519` adet
- **Üretim farkı (`production_gap`):** `-22513` adet (*Plan karşılanmadı. Üretim açığı: 22513 adet.*)
- **Plan gerçekleşme (`attainment_pct`):** `%92,32` (std `ddof=0`: `10,12` puan)
- **Toplam duruş (`total_downtime_hours`):** `223,375` saat (`159` duruşlu kayıt)
- **Kullanılabilirlik (`availability_pct`):** `%94,89`
- **Kapasite kullanım oranı (`capacity_utilization_pct`):** `%80,72`

| Grup | Kayıt | Planlanan | Gerçekleşen | Fark | Gerçekleşme % | Duruş (saat) | Kullanılabilirlik % | Kullanım % | Duruşlu Kayıt | Std (`ddof=0`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M1** | 107 | 75892 | 70442 | -5450 | 92,82 | 41,250 | 95,18 | 80,68 | 27 | 10,20 |
| **M2** | 220 | 111936 | 104909 | -7027 | 93,72 | 63,375 | 96,40 | 82,79 | 67 | 7,58 |
| **M3** | 109 | 31382 | 28317 | -3065 | 90,23 | 63,250 | 92,75 | 77,32 | 34 | 11,69 |
| **M5** | 110 | 73822 | 66851 | -6971 | 90,56 | 55,500 | 93,69 | 79,13 | 31 | 12,04 |
| **P-A** | 220 | 131311 | 121756 | -9555 | 92,72 | 83,500 | 95,26 | 80,99 | 69 | 9,05 |
| **P-B** | 213 | 107065 | 99582 | -7483 | 93,01 | 83,875 | 95,08 | 81,49 | 60 | 9,97 |
| **P-C** | 113 | 54656 | 49181 | -5475 | 89,98 | 56,000 | 93,81 | 78,57 | 30 | 12,01 |
| **afternoon** | 108 | 55052 | 51631 | -3421 | 93,79 | 30,875 | 96,43 | 83,00 | 32 | 7,56 |
| **morning** | 438 | 237980 | 218888 | -19092 | 91,98 | 192,500 | 94,51 | 80,20 | 127 | 10,62 |

---

## 6. Yedi İşletme Sorusunun Yanıtları (`q1`–`q7`)

1. **q1 – Hangi makinenin plan gerçekleşme oranı en düşük?**
   - **M3 (%90,23)** (M5 %90,56, M1 %92,82, M2 %93,72).
2. **q2 – Hangi vardiyada kullanılabilirlik en düşük?**
   - **morning (%94,51)** (afternoon %96,43).
3. **q3 – Hangi ürünün toplam duruşu, hangisinin kayıt başına ortalama duruşu en yüksek?**
   - Toplam duruşta **P-B (`83,875` saat)** öndedir; ancak kayıt başına ortalama duruşta **P-C (`0,4956` saat/kayıt)** en yüksektir (P-A `0,3795`, P-B `0,3938`). *Toplam duruş kayıt sayısından (P-B: 213 kayıt, P-C: 113 kayıt) etkilendiği için birim başı riskte P-C daha kritiktir.*
4. **q4 – Planı karşılamayan kayıtların oranı ve en yüksek olduğu makine nedir?**
   - Genel oran **%77,84 (`425 / 546`)**; oran olarak en yüksek makine **M3 (%85,32)** (M5 %77,27, M2 %76,36, M1 %73,83). *Mutlak sayı olarak M2 (168 kayıt) önde görünse de günde 2 vardiya çalıştığı için oran bazında M3 daha kötüdür.*
5. **q5 – Tam haftalar içinde toplam üretim açığı en büyük hafta hangisi?**
   - **`2026-10-19` haftası (`-1720` adet)** (16 tam hafta içinde).
6. **q6 – Hangi makinede kapasite kullanım oranı en yüksek?**
   - **M2 (%82,79)** (M1 %80,68, M5 %79,13, M3 %77,32).
7. **q7 – Duruşlu ve duruşsuz kayıtlar arasında ortalama gerçekleşme oranı farkı nedir?**
   - 159 duruşlu kayıtta ortalama gerçekleşme **%80,40**, 387 duruşsuz kayıtta **%97,05**; aradaki fark **16,65 puan**dır.

---

## 7. Üretilen Analiz Dosyaları ve Dokümantasyon

- `data/clean_records.csv`: 546 temiz kayıt (MP3 `RecordStore` uyumlu)
- `data/cleaning_log.csv`: 76 satırlık temizlik günlüğü (`record_id, issue, action`)
- `data/analysis_dataset.csv`: 546 satır × 19 sütun (`RECORD_COLUMNS + DERIVED_COLUMNS`)
- `data/kpi_by_machine.csv`, `data/kpi_by_product.csv`, `data/kpi_by_shift.csv`, `data/kpi_by_day.csv`, `data/kpi_by_week.csv`
- `data/daily_series.csv` (120 gün) ve `data/weekly_summary.csv` (18 hafta)
- `docs/data_quality_rules.md`: Veri üretim ve temizlik kuralları
- `docs/module_notes.md`: A, B ve C modül notları ve MP6–MP23 aktarım tablosu
- `docs/sample_report.txt` ve `docs/screenshot.png`: Örnek rapor çıktısı ve ekran görüntüsü

---

## 8. Sonuç

Mini Proje 5 ile birlikte üretim kayıtları için uçtan uca **Pandas veri hazırlama, doğrulama, özellik mühendisliği ve KPI analizi katmanı** tamamlanmış; MP1–MP4 paketleriyle sayısal ve yapısal uyumu 148 birim ve entegrasyon testiyle doğrulanmıştır. Üretilen temiz veri setleri ve KPI tabloları doğrudan **Mini Proje 6 (Üretim Dashboard)** ve sonraki veritabanı/ML modüllerine girdi sağlamaya hazırdır.
