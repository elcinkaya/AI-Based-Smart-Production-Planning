# Mini Proje 3 – CSV/JSON Tabanlı Üretim Kayıt Sistemi

## Amaç

Bu mini proje, veritabanına geçmeden önce günlük üretim kayıtlarının (**tarih**, **vardiya**, **makine kimliği**, **ürün kodu**, **planlanan miktar**, **gerçekleşen miktar**, **duruş süresi**) **CSV** veya **JSON** dosyalarında kalıcı olarak saklanması, program kapatılıp yeniden açıldığında kayıtların korunması ve okunan kayıtlardan **plan–gerçekleşen farkı** ile **temel performans göstergelerinin (KPI)** hesaplanıp raporlanması altyapısını kurar.

23 mini projelik yol haritasının **3. adımı** (Sprint 1) olup, ana proje olan **AI-Based Smart Production Planning and Decision Support System** için veri kalıcılığı ve üretim performans izleme temelini oluşturur.

## Kurulum ve Gereksinimler

- **Python:** 3.10+
- **Bağımlılıklar:** Yalnızca Python standart kütüphanesi (`csv`, `json`, `datetime`, `os`, `random`, `enum`, `tempfile`, `unittest`). Harici paket gerekmez (`requirements.txt`).

```bash
cd mini-projects/03-production-record-system
python main.py
```

## Çalıştırma ve Menü Seçenekleri

Uygulama açılışta kayıt dosyasının yolunu sorar (varsayılan: `data/records.csv`) ve `data/sample_factory.json` içerisindeki geçerli makine (`M1`–`M5`) ve ürün (`P-A`, `P-B`, `P-C`) kimlikleriyle `RecordStore` deposunu başlatır:

1. **Yeni üretim kaydı ekle:** Tarih (`YYYY-MM-DD`), vardiya (`morning`, `afternoon`, `night`), makine, ürün, planlanan miktar, gerçekleşen miktar ve duruş süresini sırayla sorar; hatalı girişlerde uyarı verip tekrar sorar. Sayısal girdiler Mini Proje 1'in `get_number` fonksiyonu ile doğrulanır.
2. **Kayıtları listele:** Tüm kayıtları veya isteğe bağlı filtrelerle (tarih aralığı, makine, ürün, vardiya – `AND` birleşimli) tablo halinde listeler.
3. **Genel performans özeti:** Depodaki tüm kayıtlar için kapsam ve genel KPI raporunu yazdırır.
4. **Makine / ürün / gün bazında özet:** Genel özetin yanı sıra seçilen kırılıma (`machine_id`, `product_code`, `production_date`) göre grup bazlı KPI özetini gösterir.
5. **Örnek veri üret ve dosyaya yaz:** `generate_records` ile tohumlu (`seed=42`) tekrarlanabilir sentetik kayıtlar üretir ve `RecordStore.add_records` ile atomik olarak dosyaya yazar.
6. **Dosya biçimini dönüştür (CSV ↔ JSON):** `convert_records_file` ile `.csv` ve `.json` dosyaları arasında çift yönlü dönüşüm yapar.
7. **Çıkış:** Programı güvenli şekilde sonlandırır; kayıtlar dosyada kalıcı olarak korunur.

## Modelleme ve Sentetik Veri Üretim Kuralları

- **Vardiya Süresi:** Bir kayıt, bir makinenin tek bir vardiyadaki üretim özetidir (`SHIFT_HOURS = 8.0` saat).
- **Benzersizlik Kuralı:** Aynı `(production_date, shift, machine_id)` üçlüsü için yalnızca bir kayıt bulunabilir.
- **Ham Veri Saklama:** `production_gap`, `attainment_pct` ve `availability_pct` gibi türetilmiş KPI değerleri dosyaya yazılmaz; okunan ham kayıtlardan hesaplanır.
- **Sentetik Veri Üretici (`generate_records`):**
  - Küresel `random` yerine izole `random.Random(seed)` kullanılır; aynı tohum her zaman aynı veriyi üretir.
  - Yalnızca uygun makineler (`machine.is_available() == True`; `M1`, `M2`, `M3`, `M5`) kayıt üretir; arızalı (`M4 - broken`) veya bakımdaki makineler atlanır.
  - Günlük vardiya sayısı `max(1, round(working_hours / 8.0))` ile belirlenir (`M2` günde 2 vardiya, diğerleri 1 vardiya → günde 5 kayıt, 30 günde 150 kayıt).
  - Vardiya kapasitesi Mini Proje 1 fonksiyonları (`theoretical_capacity` ve `effective_capacity`) ile hesaplanır.
  - `planned_units = round(shift_capacity * uniform(0.80, 1.00))`
  - `downtime_hours`: %30 olasılıkla `round(uniform(0.25, 3.0) * 4) / 4`, aksi halde `0.0`
  - `actual_units = max(0, round(planned_units * uniform(0.90, 1.05) * (1 - downtime_hours / 8)))`

## KPI Tanımları

- **Üretim Farkı (`production_gap`):** `actual_units - planned_units` (pozitif: fazla üretim, negatif: üretim açığı, `0`: tam gerçekleşme)
- **Plan Gerçekleşme (`attainment_pct`):** `actual_units / planned_units * 100`
- **Kullanılabilirlik (`availability_pct`):** `(kayıt_sayısı * 8 - toplam_duruş_saati) / (kayıt_sayısı * 8) * 100`
- **Plan Karşılama (`plan_met`):** `total_actual_units >= total_planned_units`

Hesaplamalarda sayılar yuvarlanmaz; yuvarlama yalnızca `report.py` içinde kullanıcıya gösterilen raporlarda yapılır.

## Örnek Çıktı (8 Sabit Test Kaydı – `data/test_records.csv`)

```text
==============================================
      ÜRETİM KAYIT PERFORMANS RAPORU
==============================================
Kapsam
  Kayıt sayısı          : 8
  Tarih aralığı         : 2026-10-01 – 2026-10-03
----------------------------------------------
Genel Sonuçlar
  Planlanan üretim      : 4510 adet
  Gerçekleşen üretim    : 4366 adet
  Üretim farkı          : -144 adet
  Plan gerçekleşme      : %96.81
  Toplam duruş          : 5.00 saat
  Kullanılabilirlik     : %92.19
----------------------------------------------
Makine Bazında
  M1 : planlanan 2400, gerçekleşen 2296, fark -104, %95.67
  M2 : planlanan 1130, gerçekleşen 1120, fark -10, %99.12
  M3 : planlanan 980, gerçekleşen 950, fark -30, %96.94
----------------------------------------------
DURUM: PLAN KARŞILANMADI
Üretim açığı: 144 adet
==============================================
```

## Testler

Tüm birim ve kalıcılık testleri `tempfile.TemporaryDirectory()` içinde izole olarak çalışır; gerçek `data/` dosyalarını değiştirmez:

```bash
python -m unittest discover tests
```

- `tests/test_record.py`: `ProductionRecord` ve `Shift` doğrulama, serileştirme ve eşitlik testleri (Kişi A)
- `tests/test_generate_records.py`: Sentetik veri üretici determinizm ve kapasite sınırı testleri (Kişi A)
- `tests/test_storage.py`: CSV/JSON okuma, atomik yazma, ekleme, dönüştürme ve bozuk dosya testleri (Kişi B)
- `tests/test_record_store.py`: `RecordStore` CRUD, mükerrerlik, filtreleme ve doğrulama testleri (Kişi B)
- `tests/test_analysis.py`: KPI hesaplama, gruplama ve rapor biçimi birim testleri (Kişi C)
- `tests/test_persistence.py`: Kapat-aç uçtan uca kalıcılık testleri (`RecordStore` yenileme, ayrı `subprocess` ve `main.py` süreç testleri) (Kişi C)

## Dosya ve Klasör Yapısı

```text
03-production-record-system/
├── main.py                          # Kişi C – 7 seçenekli Türkçe menü uygulaması
├── factory_model/                   # Mini Proje 2 kopyası (değiştirilmez)
├── production_records/
│   ├── __init__.py                  # Kişi C – dışa açılan sınıf ve fonksiyonlar
│   ├── inputs.py                    # Mini Proje 1 kopyası (get_number, değiştirilmez)
│   ├── record.py                    # Kişi A – Shift, SHIFT_HOURS, ProductionRecord
│   ├── generate_records.py          # Kişi A – tohumlu sentetik veri üretici
│   ├── storage.py                   # Kişi B – JSON/CSV okuma, yazma, ekleme, dönüştürme
│   ├── record_store.py              # Kişi B – RecordStore
│   ├── analysis.py                  # Kişi C – KPI hesaplama fonksiyonları
│   └── report.py                    # Kişi C – Türkçe performans raporu ve tablo
├── tests/
│   ├── test_record.py               # Kişi A
│   ├── test_generate_records.py     # Kişi A
│   ├── test_storage.py              # Kişi B
│   ├── test_record_store.py         # Kişi B
│   ├── test_analysis.py             # Kişi C
│   └── test_persistence.py          # Kişi C – kapat-aç uçtan uca testi
├── data/
│   ├── sample_factory.json          # Mini Proje 2 kopyası
│   ├── test_records.json / .csv     # Kişi A – 8 sabit test kaydı
│   └── sample_records.json / .csv   # Kişi A – üretilmiş örnek veri (tohum 42, 30 gün, 150 kayıt)
├── docs/
│   ├── screenshot.png               # Kişi C – örnek uygulama ve rapor çıktısı görseli
│   ├── format_comparison.md         # Kişi C – 1000 kayıtlık CSV ve JSON karşılaştırması
│   └── module_notes.md              # Ekip – ana projeye taşınacak modül notları
├── README.md                        # Kişi C
└── requirements.txt
```

## Ekip ve Görev Dağılımı

- **Kişi A:** Kayıt modeli (`record.py`), sentetik veri üretici (`generate_records.py`), sabit/örnek veri dosyaları ve model testleri
- **Kişi B:** CSV/JSON dosya depolama (`storage.py`), `RecordStore` (`record_store.py`) ve depolama testleri
- **Kişi C:** KPI analizi (`analysis.py`), raporlama (`report.py`), menü uygulaması (`main.py`), paket arayüzü (`__init__.py`), analiz/kalıcılık testleri ve dokümantasyon
