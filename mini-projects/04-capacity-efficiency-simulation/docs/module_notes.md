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

### 2.1 Sorumluluk Kapsamı
- `capacity_simulation/generation.py`: Kontrollü rastgele matrisler, planlanan/gerçekleşen üretim ve `simulate()`.
- `tests/test_generation.py`: Şekiller, aralıklar, tekrarlanabilirlik, çizim sırası, duruş kuralları, Bölüm 7.2 sabit örneği, hatalı girdiler.
- `tests/test_simulation.py`: Bölüm 7.3 altın değerleri ve tohumdan bağımsız özellik testleri.
- `docs/data_generation_rules.md`: Bölüm 3.2–3.4'ün sade anlatımı.

### 2.2 Fonksiyonlar (`generation.py`)
```python
create_rng(seed)                                                    # np.random.default_rng(seed)
generate_efficiency_matrix(rng, efficiency_min_pct, efficiency_max_pct, days)  # (M,), (M,) -> (M, D) float64 – çizim 1
generate_load_factor_matrix(rng, shape)                            # (M, D) float64 – çizim 2
generate_downtime_matrix(rng, shape, working_hours)                # (M, D) float64 – çizim 3 ve 4 (bu sırayla)
generate_performance_factor_matrix(rng, shape)                     # (M, D) float64 – çizim 5
calculate_planned_units(effective_capacity, load_factor)           # (M, D) int64, deterministik
calculate_actual_units(planned_units, performance_factor, downtime_hours, working_hours)  # (M, D) int64, deterministik
simulate(config) -> SimulationResult
```
- `simulate` sırası: verimlilik → efektif kapasite (`capacity.py`) → yük oranı → planlanan → duruş → performans oranı → gerçekleşen. Tek `rng` bir kez oluşturulur; çizim sırası ve şekilleri Bölüm 3.3 ile birebir aynıdır.
- Kapasite yalnızca A'nın `calculate_theoretical_capacity_array` / `calculate_effective_capacity_array` fonksiyonlarıyla hesaplanır; sabitler `models.py`'den okunur, yeniden tanımlanmaz.
- Yuvarlama `np.rint` (yarıda çifte). Duruş `np.rint(x / 0.25) * 0.25` (= `round(x × 4) / 4`) ve `working_hours[:, None]` ile sınırlıdır. Çizim 4, duruş olmayan hücreler için de tam matris olarak çekilir.
- Hatalar: `planned_units < 1` → `ValueError`; şekil uyuşmazlığı, metin içeren dizi, aralık dışı değer → `ValueError`; yanlış `rng`/`shape`/`config` türü → `TypeError` (Türkçe mesaj). Python döngüsü, global `np.random.*`, `print`/`input` yoktur; girdi dizileri değiştirilmez.

### 2.3 Doğrulama
- Bölüm 7.2 sabit örneği: planlanan `[[816, 768, 432], [576, 1216, 1280]]`, gerçekleşen `[[816, 691, 324], [558, 1216, 1280]]`, toplam 5088 / 4885.
- Bölüm 7.3 altın değerleri (tohum 42, 30 gün, NumPy 2.4.4, Python 3.12.6): 80449 / 73774 / −6675, %91,70, 65,25 saat, 37 duruşlu makine–gün, %94,56, min planlanan 233, verimlilik ort. 78,73, efektif kapasite 745,57 / 286,24 / 289,64 / 1209,76 — hepsi birebir tuttu.
- Özellik testleri: aynı tohum → `equals()` True, tohum 43 → False; verimlilik makine aralığında; `1 ≤ planned_units ≤ ceil(effective_capacity)`; duruş 0,25'in katı ve `≤ working_hours`; tam duruşta `actual_units = 0`; yapılandırma değişmiyor; küresel `np.random` durumu değişmiyor.

### 2.4 Entegrasyon Notları (Kişi C için)
- `simulate(config)` saf bir fonksiyondur; sonuç doğrudan `SimulationResult` olarak `stats.py`, `export.py` ve `report.py`'ye verilebilir.
- `load_factor` ve `performance_factor` sonuçta saklanmaz (Bölüm 3.2 sözleşmesi); dışa aktarımda yalnızca `SimulationResult` alanları kullanılır.
- Özet sözlüğü (`plan_met`, `status_message`, MP3 KPI fonksiyonları) C'nin `summarize_simulation` fonksiyonundadır; `test_simulation.py` toplamları yalnızca altın değer kontrolü için doğrudan NumPy ile hesaplar.

### 2.5 Ana Projeye Taşınacak Parçalar
- `simulate` ve `generate_*` fonksiyonları: MP9 canlı veri üreticisi, MP11–13 uzun dönem sentetik veri, MP17 arıza senaryosunda yapılandırma değiştirilip yeniden çalıştırma, MP18 SimPy parametreleri.
- `calculate_planned_units` / `calculate_actual_units`: gerçek veriyle aynı formüllerin deterministik uygulanması.

---

## 3. İstatistik, Rapor, Dışa Aktarım ve Entegrasyon (Kişi C)

_Kişi C tarafından doldurulacak._
