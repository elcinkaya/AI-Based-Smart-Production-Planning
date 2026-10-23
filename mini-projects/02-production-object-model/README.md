# Mini Proje 02: Fabrika Nesne Modeli (Factory Object Model)

Bu proje, **AI-Based Smart Production Planning and Decision Support System** ana projesinin 2. mini projesidir (Sprint 1). Üretim sistemindeki üç temel varlığı (`Machine`, `Product`, `ProductionLine`) nesne yönelimli programlama (OOP) ilkelerine uygun olarak modeller ve sonraki mini projeler için standart bir veri sözleşmesi (data contract) sunar.

---

## 1. Amaç ve Kapsam

- **Product Modeli**: Ürün kodu (`product_code`), ürün adı (`name`), parça başına işlem süresi (`processing_time_sec`) ve planlama önceliği (`priority`) bilgilerini tutar.
- **Machine Modeli**: Makine kapasitesi, çalışma saati, çevrim süresi, verimlilik yüzdesi, operasyonel durumu (`MachineStatus`), çalışma süresi sayacı ve bakım aralığını modeller. Efektif/teorik kapasite hesabı için Mini Proje 1'in hesaplama fonksiyonlarını kullanır.
- **ProductionLine Modeli**: Hatta bağlı makineleri ve uyumlu ürünleri tutar. Paralel çalışan makinelerin efektif kapasitelerini toplar, ürün bazlı kapasite hesaplar ve bakım ihtiyacı olan makineleri tespit eder.
- **Serileştirme ve Entegrasyon**: Tüm nesneler JSON ve CSV formatlarına kolayca aktarılabilir ve geri yüklenebilir (`to_dict`, `from_dict`, `save_factory_json`, `load_factory_json`, `export_machines_csv`).

---

## 2. Modelleme Varsayımları ve Kurallar

1. **Paralel Çalışma**: Bir üretim hattındaki makineler paralel çalışır. Hat kapasitesi, o hatta bağlı ve uygun (`IDLE` veya `RUNNING`) durumdaki makinelerin efektif kapasitelerinin toplamıdır.
2. **Çevrim ve İşlem Süresi**: Makinenin kendi `cycle_time_sec` değeri varsayılandır. Belirli bir ürün için kapasite hesaplanırken o ürünün `processing_time_sec` değeri çevrim süresi yerine kullanılır.
3. **Ürün–Hat İlişkisi**: Hat nesnesi, döngüsel referansı önlemek ve veritabanı/JSON dönüşümlerini sadeleştirmek için `Product` nesnesini değil, doğrudan ürün kodunu (`product_code`) küme (`set`) olarak saklar.
4. **Makine–Hat İlişkisi**: Bir makine en fazla bir hatta bağlı olabilir. Hat, `Machine` nesnelerini tutar; makine ise bağlı olduğu hattın `line_id` değerini tutar.
5. **Makine Durumları**: `MachineStatus` enum (`IDLE`, `RUNNING`, `MAINTENANCE`, `BROKEN`). Geçişler teknik şartnamede belirtilen durum makinesine uygun olarak yürütülür; geçersiz geçişler `ValueError` fırlatır.
6. **I/O Ayrımı**: Domain sınıfları içinde `print()` veya `input()` kullanılmaz; kullanıcı etkileşimi ve konsol çıktıları yalnızca `main.py` üzerindedir.

---

## 3. Klasör ve Dosya Yapısı

```
02-production-object-model/
├── main.py                      # Demo ve konsol rapor çıktısı (Kişi C)
├── factory_model/
│   ├── __init__.py              # Paket dışa aktarımları (Kişi C)
│   ├── base.py                  # FactoryEntity temel sınıfı ve validatörler (Kişi A)
│   ├── product.py               # Product sınıfı (Kişi A)
│   ├── machine.py               # MachineStatus ve Machine sınıfı (Kişi B)
│   ├── production_line.py       # ProductionLine ve yardımcı fonksiyonlar (Kişi C)
│   ├── serialization.py         # JSON/CSV içe-dışa aktarım (Kişi A)
│   ├── sample_data.py           # Örnek 3 hat, 5 makine, 3 ürün (Kişi C)
│   └── calculations.py          # Mini Proje 1'den alınan hesaplama modülü
├── tests/
│   ├── test_product.py          # Product ve base birim testleri (Kişi A)
│   ├── test_machine.py          # Machine durum ve kapasite testleri (Kişi B)
│   ├── test_serialization.py    # JSON/CSV serileştirme testleri (Kişi A)
│   ├── test_production_line.py  # ProductionLine testleri (Kişi C)
│   ├── test_contract.py         # to_dict() veri sözleşmesi testleri (Kişi C)
│   └── test_scenarios.py        # Şartnamedeki 22 uçtan uca senaryo (Kişi C)
├── data/
│   └── sample_factory.json      # Örnek fabrika yerleşimi JSON verisi
├── docs/
│   ├── console_output.txt       # main.py demo çıktısı
│   └── module_notes.md          # Yeniden kullanılabilir sınıf ve modül notları
├── README.md                    # Proje dokümantasyonu (Kişi C)
└── requirements.txt             # Bağımlılık listesi (Standart kütüphane)
```

---

## 4. Kurulum ve Çalıştırma

Proje sadece Python standart kütüphanesini (`unittest`, `json`, `csv`, `enum`, `typing`) kullanır; harici paket bağımlılığı gerektirmez.

### Demo Betiğini Çalıştırma

```powershell
cd mini-projects/02-production-object-model
python main.py
```

### Testleri Çalıştırma

Tüm birim, sözleşme ve uçtan uca senaryo testlerini çalıştırmak için:

```powershell
cd mini-projects/02-production-object-model
python -m unittest discover tests -v
```

---

## 5. Doğrulanan Test Senaryoları (Özet)

Şartnamede tanımlanan **22 senaryo** ve **tüm sınır/hata durumları** test edilmiştir:
- **Senaryo 1–10**: Makine teorik/efektif kapasiteleri, durum geçişleri, bakım sayacı, arıza/onarım döngüsü.
- **Senaryo 11–14**: Ürünlü ve ürünsüz hat kapasiteleri (L1=1968, L2=336, L3=768 adet/gün).
- **Senaryo 15–16**: Ürün–hat uyumluluk sorguları ve `find_lines_for_product()`.
- **Senaryo 17**: Onarım sonrası hat kapasite artışı (L2: 336 → 2046 adet/gün).
- **Senaryo 18**: Bakım ihtiyacı olan makinelerin hat üzerinden filtrelenmesi.
- **Senaryo 19–20**: Mükerrer/hat çakışmalı makine ekleme kuralları ve makine çıkarma.
- **Senaryo 21–22**: JSON gidiş-dönüş tutarlılığı ve `to_dict()` anahtar sözleşmesi birebir doğrulaması.

---

## 6. Sonraki Mini Projelere Aktarılacaklar

Bu projede oluşturulan nesne modeli ve veri sözleşmesi:
- **MP-03 (CSV/JSON Kayıt)**: Olay ve durum kayıtlarında referans anahtarlar (`machine_id`, `product_code`, `line_id`).
- **MP-04 & MP-05 (NumPy & Pandas)**: Vektörel hesaplama ve DataFrame sütun adlandırması.
- **MP-07 (SmartFactoryDB)**: PostgreSQL tabloları (`machines`, `products`, `production_lines`, `line_products`).
- **MP-15 & MP-16 (OR-Tools / Çizelgeleme)**: Hat kapasite kısıtları ve uygunluk matrisleri.
- **MP-17 (Dinamik Yeniden Planlama)**: Arıza anında anlık hat kapasitesinin güncellenmesi.
- **MP-18 (SimPy Simülasyonu)**: Simülasyon kaynak modelleri.
- **MP-19 & MP-21 (Streamlit & FastAPI)**: Veri modeli ve REST API şemaları.
