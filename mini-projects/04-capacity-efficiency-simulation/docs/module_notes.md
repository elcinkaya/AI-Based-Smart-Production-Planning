# Mini Proje 4 - Modül Notları

Bu doküman, Mini Proje 4 (NumPy ile Kapasite ve Verimlilik Simülasyonu) kapsamında geliştirilen modüllerin tasarım kararlarını, veri sözleşmelerini ve ana projeye taşınacak bileşenlerini belgeler. Her kişi kendi bölümünü yazar.

---

## 1. Yapılandırma, Sonuç Modeli ve Kapasite (Kişi A)

### 1.1 Sorumluluk Kapsamı
- `capacity_simulation/models.py`: Ortak sabitler, `SimulationConfig` ve `SimulationResult`.
- `capacity_simulation/capacity.py`: Vektörel teorik ve efektif kapasite fonksiyonları (kapasite formülünün projedeki tek yeri).
- `tests/test_models.py`, `tests/test_capacity.py`: Birim testleri (Bölüm 7.1, 7.5 ve 7.2 sabit örneği).
- `data/simulation_config.json`: `SimulationConfig.from_factory(load_factory_json('data/sample_factory.json')).to_dict()` çıktısı.

### 1.2 Sabitler (`models.py`)
`DEFAULT_DAYS = 30`, `DEFAULT_SEED = 42`, `DEFAULT_START_DATE = '2026-10-01'`, `EFFICIENCY_DOWN_PCT = 10.0`, `EFFICIENCY_UP_PCT = 5.0`, `LOAD_FACTOR_RANGE = (0.80, 1.00)`, `PERFORMANCE_FACTOR_RANGE = (0.90, 1.05)`, `DOWNTIME_PROBABILITY = 0.30`, `DOWNTIME_HOURS_RANGE = (0.25, 3.0)`, `DOWNTIME_STEP_HOURS = 0.25`. Sayılar MP3 `generate_records` ile aynıdır; başka modülde tekrar tanımlanmaz.

### 1.3 `SimulationConfig`
| Alan | Tip | Kural |
| :--- | :--- | :--- |
| `machine_ids` | `list[str]` | En az 1, benzersiz, boş olamaz (`validate_non_empty_str`) |
| `working_hours` | `list[float]` | `0 < x <= 24` |
| `cycle_time_sec` | `list[float]` | `x > 0` |
| `base_efficiency_pct` | `list[float]` | `0 < x <= 100` |
| `efficiency_min_pct` | `list[float]` | `0 < x <= base_efficiency_pct` |
| `efficiency_max_pct` | `list[float]` | `base_efficiency_pct <= x <= 100` |
| `days` | `int` | `1 <= x <= 3650` |
| `start_date` | `str` | Yalnızca `YYYY-MM-DD` |
| `seed` | `int` | `x >= 0` |

- Sayısal doğrulama MP2 `validate_number` ile yapılır; geçersiz değerde `ValueError`, yanlış türde `TypeError` (Türkçe mesaj). `bool` sayı olarak kabul edilmez.
- Öznitelikler salt okunurdur; liste özellikleri her çağrıda yeni bir kopya döndürür (yapılandırma dışarıdan değiştirilemez).
- `from_factory(factory, days, seed, start_date, efficiency_down_pct, efficiency_up_pct)`: Yalnızca `is_available()` makineleri alır, `machine_id`'ye göre sıralar (MP3 kuralı). `min = base - 10`, `max = min(100, base + 5)`. Uygun makine yoksa veya türetilen min `<= 0` ise `ValueError`; fabrika sözlük değilse `TypeError`.
- `get_machine_count()`, `to_dict()` (anahtarlar öznitelik adlarıyla birebir aynı), `from_dict()` (eksik alanda `Eksik alan: ...`), `__repr__()`.

### 1.4 `SimulationResult`
| Alan | Tip / Şekil | Kural |
| :--- | :--- | :--- |
| `config` | `SimulationConfig` | – |
| `theoretical_capacity` | `float64 (M,)` | `x > 0` |
| `efficiency_pct` | `float64 (M, D)` | Makinenin `[min, max]` aralığında |
| `effective_capacity` | `float64 (M, D)` | `x > 0` |
| `planned_units` | `int64 (M, D)` | `x >= 1` |
| `downtime_hours` | `float64 (M, D)` | `0 <= x <= working_hours` |
| `actual_units` | `int64 (M, D)` | `x >= 0` |

- Kurucu sırasıyla tür (`np.ndarray`, değilse `TypeError`), dtype (yanlışsa `TypeError`), şekil (yanlışsa `ValueError`), NaN/sonsuz ve değer aralıklarını (`ValueError`) denetler. Diziler kopyalanarak saklanır.
- `get_shape() -> (M, D)`, `to_dict()` (diziler `tolist()`, `config` için `config.to_dict()`), `from_dict()`, `equals(other)` (yapılandırma ve tüm dizilerde `np.array_equal`), `__repr__()`.

### 1.5 Vektörel Kapasite (`capacity.py`)
```python
calculate_theoretical_capacity_array(working_hours, cycle_time_sec)  # (M,), (M,) -> (M,)
calculate_effective_capacity_array(theoretical_capacity, efficiency_pct)  # (M,), (M, D) -> (M, D)
```
- Formüller: `working_hours * 3600 / cycle_time_sec` ve `theoretical_capacity[:, None] * efficiency_pct / 100`. Python döngüsü yoktur, girdi dizileri değiştirilmez, sonuç `float64`'tür.
- MP1 kuralları: `working_hours <= 0` veya `> 24`, `cycle_time_sec <= 0`, `efficiency_pct <= 0` veya `> 100`, negatif teorik kapasite, şekil/boyut uyuşmazlığı, metin/bool içeren dizi, NaN ve boş dizi için `ValueError`.

### 1.6 Doğrulama
- Bölüm 7.1: Teorik `[960, 1280, 480, 1800, 960]`, efektif `[816, 1152, 336, 1710, 768]`; MP1 `theoretical_capacity` / `effective_capacity` döngüsüyle `np.allclose`.
- `from_factory` sonucu Bölüm 7.3 ile birebir aynıdır (M1, M2, M3, M5; teorik kapasite `[960, 1280, 480, 960]`).
- Bölüm 3.3 çizim sırasıyla yazılan geçici bir referans simülasyon, bu modüllerin arayüzleriyle 7.3 altın değerlerini (80449 / 73774 / −6675, 65,25 saat, 37 duruşlu gün, min planlanan 233) NumPy 2.4.4'te üretmiştir.

### 1.7 Ana Projeye Taşınacak Parçalar
- `SimulationConfig` / `SimulationResult`: sentetik veri üretiminin girdi/çıktı sözleşmesi (MP5, MP6, MP9, MP11–13, MP17).
- `calculate_effective_capacity_array`: OR-Tools ve çizelgeleme projelerinde (MP15–16) günlük kapasite kısıtının veri kaynağı (birim adet/gün).

---

## 2. Üretim ve Simülasyon (Kişi B)

_Kişi B tarafından doldurulacak._

---

## 3. İstatistik, Rapor, Dışa Aktarım ve Entegrasyon (Kişi C)

_Kişi C tarafından doldurulacak._
