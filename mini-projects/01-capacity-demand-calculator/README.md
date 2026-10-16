# Mini Proje 1 – Üretim Kapasitesi ve Talep Karşılama Hesaplayıcısı

## Amaç

Bu mini proje; kullanıcıdan günlük çalışma süresi, çevrim süresi, verimlilik oranı ve talep miktarını alıp **teorik kapasite**, **efektif kapasite**, **kapasite kullanım oranı** ve **talep karşılama durumunu** hesaplayan, sonucu anlaşılır bir üretim raporu olarak ekrana basan bir Python konsol uygulamasıdır.

23 mini projelik roadmap'in **1. adımı** olup, ana proje olan **AI-Based Smart Production Planning and Decision Support System** için temel kapasite kontrol altyapısını oluşturur.

## Kurulum

**Gereksinimler:**
- Python 3.10+
- Standart kütüphane dışında ek paket gerekmez

```bash
# Projeyi klonlayın
git clone <repo-url>
cd mini-projects/01-capacity-demand-calculator
```

## Çalıştırma

```bash
python main.py
```

Program sizi karşılama ekranıyla karşılar, ardından sırasıyla şu girdileri sorar:
1. **Günlük çalışma süresi** (saat, 0 < değer ≤ 24)
2. **Çevrim süresi** (saniye/adet, değer > 0)
3. **Verimlilik** (%, 0 < değer ≤ 100)
4. **Günlük talep** (adet, değer ≥ 0)

Hatalı girişlerde program çökmeden uyarı verir ve tekrar sorar.

## Varsayımlar

- Tüm hesaplar **tek üretim hattı** ve **tek ürün** içindir.
- Çalışma süresi saatte, çevrim süresi saniyede alınır.
- Verimlilik **yüzde** olarak girilir (örn. 85, 0.85 değil).
- Formüller:
  - Teorik kapasite = (çalışma süresi × 3600) / çevrim süresi
  - Efektif kapasite = teorik kapasite × (verimlilik / 100)
  - Kapasite kullanım oranı = (talep / efektif kapasite) × 100
  - Kapasite farkı = efektif kapasite − talep

## Örnek Çıktı

```
==============================================
        ÜRETİM KAPASİTE RAPORU
==============================================
Girdiler
  Günlük çalışma süresi : 8.0 saat
  Çevrim süresi          : 30.0 sn/adet
  Verimlilik             : %85.0
  Günlük talep           : 1000 adet
----------------------------------------------
Sonuçlar
  Teorik kapasite        : 960.00 adet/gün
  Efektif kapasite       : 816.00 adet/gün
  Kapasite kullanım      : %122.55
  Kapasite farkı         : -184.00 adet/gün
----------------------------------------------
DURUM: TALEP KARŞILANMIYOR
Kapasite açığı: 184.00 adet/gün
==============================================
```

## Testler

```bash
# Tüm testleri çalıştırma
python -m unittest discover tests

# Sadece senaryo testlerini çalıştırma
python -m unittest tests.test_scenarios
```

7 farklı senaryo test edilmektedir:
1. Kapasite fazlası (8 saat, 30 sn, %85, 700 talep)
2. Kapasite açığı (8 saat, 30 sn, %85, 1000 talep)
3. Çift vardiya fazla (16 saat, 45 sn, %90, 1000 talep)
4. Düşük verimlilik açık (8 saat, 60 sn, %70, 400 talep)
5. Sınıra yakın fazla (10 saat, 20 sn, %95, 1700 talep)
6. Tam denge (8 saat, 30 sn, %80, 768 talep)
7. Sıfır talep (8 saat, 30 sn, %85, 0 talep)

## Dosya Yapısı

```
01-capacity-demand-calculator/
├── main.py                  # Kişi C – programın giriş noktası
├── inputs.py                # Kişi A – girdi alma ve doğrulama
├── calculations.py          # Kişi B – hesaplama fonksiyonları
├── report.py                # Kişi C – rapor biçimlendirme ve yazdırma
├── tests/
│   ├── test_inputs.py       # Kişi A
│   ├── test_calculations.py # Kişi B
│   └── test_scenarios.py    # Kişi C (uçtan uca)
├── data/
│   ├── scenarios.json       # Kişi B – örnek giriş verisi ve beklenen sonuçlar
│   └── generate_data.py     # Kişi B – isteğe bağlı rastgele senaryo üretici
├── docs/
│   ├── screenshot.png       # Kişi C
│   └── module_notes.md      # Üçü birlikte
├── README.md                # Kişi C
└── requirements.txt
```

## Ekip

- **Kişi A** – Girdi ve doğrulama modülü
- **Kişi B** – Hesaplama mantığı ve senaryo verisi
- **Kişi C** – Rapor, ana akış, entegrasyon ve dokümantasyon

## Lisans

Bu proje eğitim amaçlı geliştirilmiştir.
