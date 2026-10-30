# Mini Proje 3 – Modül Notları

Bu doküman, Mini Proje 3 (CSV/JSON Tabanlı Üretim Kayıt Sistemi) kapsamında geliştirilen modüllerin teknik tasarım kararlarını, veri sözleşmelerini ve ana projeye (`AI-Based Smart Production Planning and Decision Support System`) aktarılacak bileşenlerini belgeler.

---

## 1. Kayıt Modeli ve Veri Üretici (Kişi A)

### 1.1 Sorumluluk Kapsamı
- `production_records/record.py`: `Shift` Enum sabiti, `SHIFT_HOURS` sabiti ve `ProductionRecord` etki alanı sınıfı.
- `production_records/generate_records.py`: Tohumlu (seed) ve tekrarlanabilir sentetik üretim kayıtları üreticisi.
- `tests/test_record.py`: `ProductionRecord` sınıfı ve doğrulama kuralları için birim testleri.
- `tests/test_generate_records.py`: Sentetik veri üreticisi için determinizm ve kural doğrulama birim testleri.
- `data/test_records.json` & `data/test_records.csv`: 8 adet sabit test kaydı (B ve C kişilerinin testleri için referans veri kümesi).
- `data/sample_records.json` & `data/sample_records.csv`: Örnek fabrika modeli ile tohum 42 kullanılarak üretilen 30 günlük (150 kayıt) veri kümesi.

### 1.2 Teknik Tasarım ve Veri Sözleşmesi

#### `Shift` Enum
Vardiya modellemesi `Enum` sınıfı üzerinden büyük harfli üyeler ve küçük harfli metin değerleriyle kurgulanmıştır:
- `Shift.MORNING = "morning"`
- `Shift.AFTERNOON = "afternoon"`
- `Shift.NIGHT = "night"`
- Sabit vardiya süresi: `SHIFT_HOURS = 8.0` saat.

#### `ProductionRecord` Sınıfı
Bir makinenin tek bir vardiyadaki üretim özetini temsil eder. `FactoryEntity` sınıfından türetilmemiştir (kaydın bir `name` özniteliği yoktur) ancak önceki mini projelerle belirlenen `to_dict()`, `from_dict()`, `__repr__()` ve `__eq__()` sözleşmelerine tam uyumludur.

| Alan Adı | Tür | Kural / Açıklama |
| :--- | :--- | :--- |
| `record_id` | `int \| None` | `x >= 1`. Depo tarafında atanana kadar `None`. Bool/float reddedilir. |
| `production_date` | `datetime.date` | Geçerli takvim tarihi. Kurucu ISO metin (`YYYY-MM-DD`) veya `datetime.date` kabul eder. |
| `shift` | `Shift` | `Shift` enum üyesi veya `'morning'`, `'afternoon'`, `'night'` metin değeri. |
| `machine_id` | `str` | Boş veya yalnızca boşluktan oluşan metinler reddedilir (`factory_model.base.validate_non_empty_str`). |
| `product_code` | `str` | Boş olamaz (`validate_non_empty_str`). |
| `planned_units` | `int` | `x > 0`. Sayısal `bool` ve `float` (örn. `800.0` veya `800.5`) kesinlikle reddedilir. |
| `actual_units` | `int` | `x >= 0`. `bool` ve `float` reddedilir. |
| `downtime_hours` | `float` | `0.0 <= x <= 8.0`. `bool` reddedilir. `validate_number` ile sınır kontrolü yapılır. |

#### Benzersizlik Anahtarı (`get_key()`)
Her makinenin bir vardiyada yalnızca tek bir kayıt üretebilmesi kuralı gereğince:
```python
def get_key(self) -> tuple[str, str, str]:
    return (self.production_date.isoformat(), self.shift.value, self.machine_id)
```
Bu anahtar, depolama katmanında (Kişi B - `RecordStore`) mükerrer kayıt kontrolünde doğrudan kullanılır.

### 1.3 Sentetik Veri Üretim Kuralları (`generate_records`)
- **İzole Rastgelelik:** Küresel `random` yerine `random.Random(seed)` nesnesi kullanılmıştır; böylece aynı tohum her zaman birebir aynı veriyi üretir.
- **Yalnızca Uygun Makineler:** Yalnızca `machine.is_available()` sonucu `True` olan makineler (`IDLE` veya `RUNNING`) kayıt üretir. `BROKEN` (örn. M4) ve `MAINTENANCE` durumundaki makineler atlanır.
- **Vardiya Sayısı ve Dağılımı:** Makinenin günlük vardiya sayısı `max(1, round(working_hours / 8.0))` ile hesaplanır. Vardiyalar sırayla `morning`, `afternoon`, `night` olarak atanır (M1: 1, M2: 2, M3: 1, M5: 1 -> günde 5 kayıt).
- **Vardiya Kapasitesi:** `calculate_effective_capacity(calculate_theoretical_capacity(working_hours, cycle_time_sec), efficiency_pct) / num_shifts` formülüyle (MP1 fonksiyonları) hesaplanır.
- **Ürün Rotasyonu:** Makinenin bağlı olduğu hattın uyumlu ürün kodları (`compatible_product_codes`) sıralanır ve gün indeksine göre modulo ile döndürülerek seçilir (`products[day_idx % len(products)]`).
- **Planlanan ve Gerçekleşen Miktar:**
  - `planned_units = round(shift_capacity * uniform(0.80, 1.00))` (asla vardiya kapasitesini aşmaz).
  - `downtime_hours`: %30 olasılıkla `round(uniform(0.25, 3.0) * 4) / 4`, aksi halde `0.0`.
  - `actual_units = max(0, round(planned_units * uniform(0.90, 1.05) * (1 - downtime_hours / 8)))`.

### 1.4 Sabit Test Verisi (8 Kayıt) ve Teknik Not
Word şartnamesinde "Bölüm 7.1'deki 8 sabit test kaydı"na atıf yapılmıştır ancak doküman gövdesinde Bölüm 7 yer almamaktadır.
Bu durum Kişi A tarafından tespit edilmiş, uydurma veri üretilmek yerine şartnamenin **Bölüm 3.2** (örnek 1. satır) ve **Bölüm 5** (Kişi C hedef rapor çıktısındaki kesin toplam ve makine bazlı KPI değerleri: Toplam 4510 planlanan, 4366 gerçekleşen, 5.00 saat duruş, M1=2400/2296, M2=1130/1120, M3=980/950) referans alınarak 8 kaydın tamamı bu matematiksel ve biçimsel hedefleri birebir sağlayacak şekilde kurgulanmış ve hem JSON hem CSV formatında teslim edilmiştir.

### 1.5 Ana Projeye Taşınacak Parçalar
- `ProductionRecord` sınıfı ve `Shift` enum'ı ilerleyen mini projelerde (özellikle veritabanı persistansı ve optimizasyon modüllerinde) temel veri varlığı (Entity) olarak kullanılacaktır.
- `generate_records` fonksiyonu, üretim simülasyonu ve yapay zeka model eğitim veri kümesi üretiminde temel sentetik veri sağlayıcı olarak konumlandırılacaktır.

---

## 2. Depolama ve RecordStore (Kişi B)
*(Kişi B tarafından doldurulacaktır: storage.py, record_store.py, test_storage.py, test_record_store.py)*

---

## 3. KPI Analizi, Raporlama ve Entegrasyon (Kişi C)
*(Kişi C tarafından doldurulacaktır: analysis.py, report.py, main.py, test_analysis.py, test_persistence.py)*
