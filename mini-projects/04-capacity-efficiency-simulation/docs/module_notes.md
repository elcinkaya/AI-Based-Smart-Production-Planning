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

### 3.1 Sorumluluk Kapsamı
- `capacity_simulation/stats.py`: İstatistiksel hesaplamalar (`calculate_statistics`, `ddof=0`) ve KPI özet sözlükleri (`summarize_simulation`, `summarize_by_machine`).
- `capacity_simulation/export.py`: `.npz` arşivleme, uzun biçimli CSV dışa aktarımı (`save_simulation_csv`), tamsayı paylaştırma (`split_units`) ve MP3 köprüsü (`simulation_to_records`).
- `capacity_simulation/report.py`: Çerçeveli (`====`) Türkçe simülasyon raporu (`build_simulation_report`, `print_simulation_report`).
- `capacity_simulation/benchmark.py`: Python döngüsü (MP1 tekil fonksiyonları) ile vektörel NumPy kapasite hesabının hız karşılaştırması (`compare_loop_and_numpy`).
- `capacity_simulation/__init__.py`: Paket dışa aktarımları (`__all__`).
- `main.py`: 6 seçenekli Türkçe konsol uygulaması.
- `tests/test_stats.py`, `tests/test_export.py`, `tests/test_integration.py`: Bölüm 7.1, 7.2, 7.3, 7.4 ve 7.5 kapsamındaki birim ve entegrasyon testleri.
- `data/simulation_output.csv`, `data/simulation_output.npz`, `requirements.txt`, `README.md`, `docs/screenshot.png`.

### 3.2 Fonksiyonlar ve Tasarım Kararları
```python
# stats.py
calculate_statistics(values, axis=None) -> dict          # {'mean', 'std', 'min', 'max'}, ddof=0
summarize_simulation(result) -> dict                     # Bölüm 3.5 özet sözlüğü
summarize_by_machine(result) -> dict                     # {machine_id: özet sözlüğü}

# export.py
save_simulation_npz(path, result) -> None                # np.savez, config JSON metni olarak
load_simulation_npz(path) -> SimulationResult            # allow_pickle=False, bozuk/eksikte ValueError
save_simulation_csv(path, result) -> None                # uzun biçim (M*D satır), yuvarlanmamış tam hassasiyet
split_units(total, parts) -> list[int]                   # kalan ilk parçalara dağıtılır
simulation_to_records(result, factory) -> list[ProductionRecord]  # MP3 vardiya köprüsü

# report.py
build_simulation_report(summary, machine_summaries=None) -> str
print_simulation_report(summary, machine_summaries=None) -> None

# benchmark.py
compare_loop_and_numpy(machine_count=1000, days=365) -> dict
build_benchmark_report(benchmark) -> str
print_benchmark_report(benchmark) -> None
```
- **Standart Sapma (`ddof=0`):** Popülasyon standart sapması kullanılır (`STD_DDOF = 0`). MP5 Pandas karşılaştırmalarında `df.std(ddof=0)` verilmelidir.
- **MP3 KPI Yeniden Kullanımı:** Toplam KPI'lar (`production_gap`, `attainment_pct`, `availability_pct`) ve Türkçe `status_message` metinleri doğrudan MP3 `production_records/analysis.py` fonksiyonlarıyla hesaplanır. Sayılar `stats.py` içinde yuvarlanmaz; yalnızca `report.py` aşamasında 2 ondalık basamağa biçimlendirilir.
- **MP3 Köprüsü (`simulation_to_records`):** Her makine–gün hücresi `working_hours / SHIFT_HOURS` (yalnızca 8, 16, 24 saat; tam sayı değilse `ValueError`) kadar vardiyaya (`morning`, `afternoon`, `night`) bölünür. `planned_units` ve `actual_units` değerleri `split_units` ile paylaştırılır, `downtime_hours` eşit bölünür, ürün kodu hattın sıralı uygun ürünlerinden gün indeksine göre döndürülerek seçilir. Toplam planlanan, gerçekleşen ve duruş birebir korunur.

### 3.3 Doğrulama ve Ölçüm Sonuçları
- **Bölüm 7.2 (2×3 Sabit Örnek):** `summarize_simulation`, `summarize_by_machine`, `calculate_statistics` (tüm hücreler, `axis=1`, `axis=0`) ve `build_simulation_report` çıktıları şartnamedeki hedef metinle karakter karakter aynıdır.
- **Bölüm 7.3 & 7.4 (Altın Değerler ve Köprü):** Tohum 42, 30 günlük simülasyon `simulation_to_records` ile 150 `ProductionRecord` (`M1: 30, M2: 60, M3: 30, M5: 30`) üretir; `days=120` ile 600 kayıt üretilir. `RecordStore.add_records` ve `summarize_records` sonuçları `summarize_simulation` ile birebir örtüşür (`total_planned_units=80449`, `total_actual_units=73774`, `production_gap=-6675`, `attainment_pct=91.70%`, `total_downtime_hours=65.25`, `availability_pct=94.56%`).
- **Hız Karşılaştırması (`1000 makine × 365 gün = 365.000 hücre`, Python 3.12.0, NumPy 2.4.4):** Python döngüsü `0.0887 sn`, NumPy vektörel hesap `0.0029 sn` (~`30.4 kat` hızlanma, `np.allclose == True`).
- **Python / NumPy Uyumluluğu Notu:** Şartnamede genel alt sınır `Python 3.10+` olarak geçse de sabitlenen `numpy==2.4.4` sürümü yalnızca `Python >= 3.11` desteklemektedir (Python 3.10 ile uyumsuzdur). Çalışma ve doğrulama Python 3.12 ile gerçekleştirilmiştir.

### 3.4 Ana Projeye ve Sonraki Mini Projelere Taşınacak Parçalar
| Hedef Proje | Taşınacak Modül / Fonksiyon | Kullanım Amacı |
| :--- | :--- | :--- |
| **MP5 – Pandas Analizi** | `simulation_to_records`, `save_simulation_csv`, `data/simulation_output.csv` | 120 günlük (600 vardiya kaydı) veya 30 günlük (120 makine-gün) tablosal veri kaynağı; `ddof=0` ile özet doğrulaması |
| **MP6 – Dashboard** | `summarize_simulation`, `summarize_by_machine`, `SIMULATION_SUMMARY_KEYS` | KPI kartları ve makine-gün matris görselleştirmeleri |
| **MP10 – İstatistiksel EDA** | `calculate_statistics` (`ddof=0`) | Dağılım ve betimsel istatistik referansı |
| **MP15–16 – OR-Tools Çizelgeleme** | `load_simulation_npz`, `effective_capacity` matrisi | Günlük makine kapasite kısıtlarının okunması |
| **MP23 – Büyük Proje Entegrasyonu** | `capacity_simulation` paketi (`__init__.py` dışa aktarımları) | Gerçek veri olmadığında tekrarlanabilir sentetik üretim ve kapasite veri kaynağı |
