# Mini Proje 4: NumPy ile Kapasite ve Verimlilik Simülasyonu

**AI-Based Smart Production Planning and Decision Support System** ana projesine hazırlık kapsamında geliştirilen 23 mini projenin 4. adımıdır. Birden fazla makinenin teorik/efektif kapasite ve günlük üretim değerlerini Python döngüleri yerine **NumPy vektörel dizi işlemleriyle** hesaplayarak tekrarlanabilir (`seed=42`) sentetik üretim verisi üretir ve Mini Proje 3 kayıt sistemiyle (`ProductionRecord` / `RecordStore`) entegre eder.

## 1. Amaç ve Kapsam

- Mini Proje 2 örnek fabrikasındaki üretime uygun makinelerden (`M1`, `M2`, `M3`, `M5`) kapasite dizileri oluşturmak (`factory_model/`).
- `np.random.default_rng(seed)` ile kontrollü ve tekrarlanabilir günlük verimlilik, yük oranı, duruş ve performans matrisleri `(M, D)` üretmek.
- Teorik ve efektif kapasiteyi NumPy yayınlama (`broadcasting`) ile vektörel hesaplamak.
- Ortalama, popülasyon standart sapması (`ddof=0`), minimum ve maksimum istatistiklerini ve MP3 uyumlu KPI özetlerini (`production_gap`, `attainment_pct`, `availability_pct`) raporlamak.
- Sonuçları `.npz` (dizi arşivi), uzun biçimli `.csv` ve Mini Proje 3 `ProductionRecord` vardiya kayıtlarına dönüştürmek.
- Python döngüsü ile NumPy vektörel hesaplamasının hızını karşılaştırmak (`benchmark.py`).

## 2. Kurulum ve Çalıştırma

> **Önemli Uyumluluk Notu (Python & NumPy):** Proje planında genel dil gereksinimi `Python 3.10+` olarak belirtilmiş olsa da, tekrarlanabilir altın değerlerin üretildiği **`numpy==2.4.4` sürümü yalnızca Python 3.11 ve üzerini (`>=3.11`) desteklemektedir** (Python 3.10 için `numpy 2.4.4` paketi mevcut değildir). Bu nedenle projeyi çalıştırmak için **Python 3.11+** (önerilen: Python 3.12) kullanılmalıdır.

```bash
cd mini-projects/04-capacity-efficiency-simulation
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

### Birim ve Entegrasyon Testlerini Çalıştırma

```bash
python -m unittest discover tests -v
```

## 3. Modelleme Varsayımları ve Sentetik Veri Kuralları

Ayrıntılı açıklama [`docs/data_generation_rules.md`](docs/data_generation_rules.md) belgesindedir. Özet kurallar:

1. **Boyut ve Makine Seti:** Matrisler `(M, D)` = `(n_machines, n_days)` şeklindedir (`axis=0` makine, `axis=1` gün). Yalnızca `is_available()` olan makineler (`M1`, `M2`, `M3`, `M5`; `M4` arızalı olduğu için hariç) `machine_id` sırasıyla dahil edilir.
2. **Rastgelelik ve Tekrarlanabilirlik Sözleşmesi:** Yalnızca `np.random.default_rng(seed)` kullanılır; küresel `np.random.*` çağrıları yasaktır. `simulate(config)` içinde çizimler tam olarak şu sırayla ve `(M, D)` boyutunda yapılır:
   - **Çizim 1 (`efficiency_pct`):** `rng.uniform(low[:, None], high[:, None], size=(M, D))` — varsayılan aralık `[base - 10, min(100, base + 5)]`.
   - **Çizim 2 (`load_factor`):** `rng.uniform(0.80, 1.00, size=(M, D))`.
   - **Çizim 3 (`downtime occurrence`):** `rng.random((M, D)) < 0.30` (%30 duruş olasılığı).
   - **Çizim 4 (`downtime amount`):** `rng.uniform(0.25, 3.0, size=(M, D))` → çeyrek saate yuvarlanır (`np.rint(x / 0.25) * 0.25`) ve `working_hours[:, None]` ile sınırlanır.
   - **Çizim 5 (`performance_factor`):** `rng.uniform(0.90, 1.05, size=(M, D))`.
3. **Vektörel Formüller:**
   - `theoretical_capacity = working_hours * 3600 / cycle_time_sec` (`float64 (M,)`)
   - `effective_capacity = theoretical_capacity[:, None] * efficiency_pct / 100` (`float64 (M, D)`)
   - `planned_units = np.rint(effective_capacity * load_factor)` (`int64 (M, D)`, `< 1` ise `ValueError`)
   - `actual_units = np.maximum(0, np.rint(planned_units * performance_factor * (1 - downtime_hours / working_hours[:, None])))` (`int64 (M, D)`)
4. **İstatistik ve KPI Kuralları:**
   - Standart sapma her yerde `ddof=0` (popülasyon) ile hesaplanır.
   - Toplam KPI'lar MP3 `analysis.py` fonksiyonlarıyla (`calculate_production_gap`, `calculate_attainment_pct`, `calculate_availability_pct`) hesaplanır.

## 4. Varsayılan Simülasyon Çıktısı (Tohum 42, 30 Gün)

```text
==============================================
  KAPASİTE VE VERİMLİLİK SİMÜLASYON RAPORU
==============================================
Kapsam
  Makine sayısı         : 4
  Gün sayısı            : 30
  Tarih aralığı         : 2026-10-01 – 2026-10-30
----------------------------------------------
Genel Sonuçlar
  Planlanan üretim      : 80449 adet
  Gerçekleşen üretim    : 73774 adet
  Üretim farkı          : -6675 adet
  Plan gerçekleşme      : %91.70
  Toplam duruş          : 65.25 saat
  Kullanılabilirlik     : %94.56
----------------------------------------------
İstatistikler (tüm makine-günler)
                           Ortalama      Std      Min      Maks
  Verimlilik (%)              78.73     8.74    60.34     94.51
  Efektif kapasite (adet)    745.57   286.24   289.64   1209.76
  Gerçekleşen üretim (adet)  614.78   255.49   180.00   1178.00
----------------------------------------------
Makine Bazında
  M1 : planlanan 21303, gerçekleşen 19202, fark -2101, %90.14
  M2 : planlanan 30363, gerçekleşen 28142, fark -2221, %92.69
  M3 : planlanan 8586, gerçekleşen 8013, fark -573, %93.33
  M5 : planlanan 20197, gerçekleşen 18417, fark -1780, %91.19
----------------------------------------------
DURUM: PLAN KARŞILANMADI
Üretim açığı: 6675 adet
==============================================
```

## 5. Döngü / NumPy Hız Karşılaştırması Sonucu (`benchmark.py`)

`compare_loop_and_numpy(machine_count=1000, days=365)` fonksiyonuyla **365.000 makine–gün hücresi** üzerinde yapılan gerçek ölçüm (Python `3.12.0`, NumPy `2.4.4`):

| Yöntem | Süre (sn) | Hızlanma | Sonuç Eşitliği (`np.allclose`) |
| :--- | ---: | ---: | :--- |
| Python `for` döngüsü (MP1 tekil fonksiyonları) | `0.0887 sn` | `1.0x` | Evet |
| NumPy vektörel dizi hesabı (`capacity.py`) | `0.0029 sn` | **`30.4 kat`** | Evet (`True`) |

## 6. Proje Klasör Yapısı

```text
04-capacity-efficiency-simulation/
├── main.py                          # Konsol menü uygulaması (Kişi C)
├── factory_model/                   # MP2 paketi kopyası (DEĞİŞTİRİLMEZ)
├── production_records/              # MP3 paketi kopyası (DEĞİŞTİRİLMEZ)
├── capacity_simulation/
│   ├── __init__.py                  # Dışa açılan sınıf ve fonksiyonlar (Kişi C)
│   ├── models.py                    # Sabitler, SimulationConfig, SimulationResult (Kişi A)
│   ├── capacity.py                  # Vektörel kapasite fonksiyonları (Kişi A)
│   ├── generation.py                # Rastgele matrisler ve simulate() (Kişi B)
│   ├── stats.py                     # İstatistik ve KPI özetleri (Kişi C)
│   ├── export.py                    # .npz, CSV ve MP3 köprüsü (Kişi C)
│   ├── report.py                    # Rapor metni üretimi (Kişi C)
│   └── benchmark.py                 # Döngü / NumPy hız karşılaştırması (Kişi C)
├── tests/                           # Birim, altın değer ve entegrasyon testleri (176 test)
├── data/
│   ├── sample_factory.json          # MP2 örnek fabrika verisi
│   ├── simulation_config.json       # Örnek simülasyon yapılandırması
│   ├── simulation_output.csv        # Tohum 42, 30 gün uzun biçim CSV (120 satır)
│   └── simulation_output.npz        # Tohum 42, 30 gün NumPy dizi arşivi
├── docs/
│   ├── screenshot.png               # Konsol çıktı görüntüsü
│   ├── data_generation_rules.md     # Sentetik veri üretim kuralları
│   └── module_notes.md              # Modül ve ana proje entegrasyon notları
├── README.md
└── requirements.txt                 # numpy==2.4.4
```
