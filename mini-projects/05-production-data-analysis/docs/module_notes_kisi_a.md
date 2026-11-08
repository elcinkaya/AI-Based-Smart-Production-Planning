# Mini Proje 5 – Modül Notları (Kişi A Bölümü)

> **Birleştirme Notu (Kişi C için):** Bu dosya, ortak `docs/module_notes.md` içinde yer alacak **"1. Şema, Ana Tablolar, Yükleme ve Veri Kaynağı (Kişi A)"** bölümüdür. Birleştirme (merge) aşamasında doğrudan `docs/module_notes.md` dosyasının 1. bölümü olarak eklenebilir.

---

## 1. Şema, Ana Tablolar, Yükleme ve Veri Kaynağı (Kişi A)

### 1.1 Sorumluluk Kapsamı
- `production_analysis/schema.py`: Sütun adları, vardiya değerleri, anahtar alanlar, temizlik sorun kodları (`ISSUE_ACTIONS`), türetilmiş sütunlar (`DERIVED_COLUMNS`) ve KPI tablosu sütunları (`KPI_COLUMNS`).
- `production_analysis/masters.py`: Fabrika makine ve ürün ana tabloları (`build_machine_master`, `build_product_master`).
- `production_analysis/loading.py`: Ham CSV/JSON DataFrame yükleme (`load_records_dataframe`) ve MP3 `ProductionRecord` sınır dönüşümleri (`records_to_dataframe`, `dataframe_to_records`).
- `production_analysis/dataset.py`: MP4 simülasyonu + MP3 `RecordStore` üzerinden 600 satırlık temiz ham veri ve 610 satırlık kirli veri üretim hattı (`build_clean_records`, `write_raw_datasets`).
- `production_analysis/fault_injection.py`: Kontrollü hata enjeksiyonu (`FAULT_PLAN`, `DUPLICATE_COUNT`, `inject_faults`, `save_dirty_records`).
- `tests/test_schema_masters.py`, `tests/test_loading.py`, `tests/test_fault_injection.py`: Bölüm 7.1, 7.2, 7.6 (#4, #5, #6) ve 7.7 birim testleri.
- Örnek veri çıktıları: `data/raw_records_clean.csv` (600 satır), `data/raw_records_dirty.csv` (610 satır), `data/raw_records_dirty.json` (610 kayıt), `data/fault_injection_log.csv` (76 satır).

### 1.2 Şema ve Veri Sözleşmesi (`schema.py`)
- `RECORD_COLUMNS`: MP3 `CSV_COLUMNS` ile birebir aynı sırada `['record_id', 'production_date', 'shift', 'machine_id', 'product_code', 'planned_units', 'actual_units', 'downtime_hours']`.
- `VALID_SHIFTS`: MP3 `Shift` enum değerlerinden türetilir (`['morning', 'afternoon', 'night']`).
- `KEY_FIELDS`: Eksikliğinde `missing_key_field` olarak işaretlenip silinecek alanlar (`['production_date', 'shift', 'machine_id', 'product_code', 'planned_units']`).
- `ISSUE_ACTIONS`: Bölüm 3.3'teki 11 sorun kodunun (`missing_key_field`, `missing_actual_units`, `missing_downtime_hours`, `invalid_date`, `invalid_shift`, `unknown_machine_id`, `unknown_product_code`, `invalid_planned_units`, `invalid_actual_units`, `invalid_downtime_hours`, `duplicate_key`) eylem eşlemesi. Yalnızca `missing_downtime_hours` `'filled'`, diğer 10 kod `'dropped'` değerindedir.
- `DERIVED_COLUMNS` (11 sütun) ve `KPI_COLUMNS` (12 sütun): Kişi B ve Kişi C'nin doğrudan içe aktaracağı standart sütun listeleridir.

### 1.3 Makine ve Ürün Ana Tabloları (`masters.py`)
```python
build_machine_master(factory: dict) -> pd.DataFrame
build_product_master(factory: dict) -> pd.DataFrame
```
- `factory`, MP2 `load_factory_json` çıktısıdır. Satır sırası fabrikadaki makine/ürün sırasıyla aynıdır (`index = 0..n-1`).
- Makine kapasiteleri yeni bir formül yazılmadan doğrudan MP4'ün vektörel fonksiyonlarıyla (`calculate_theoretical_capacity_array`, `calculate_effective_capacity_array`) hesaplanır (`efficiency_pct` `(M, 1)` boyutuna getirilip sonuç `.ravel()` ile düzleştirilir).
- `shift_count = np.maximum(1, np.rint(working_hours / SHIFT_HOURS)).astype(np.int64)` (MP3 kuralı) ve `shift_effective_capacity = effective_capacity / shift_count`.
- `is_available` sütunu MP2 `Machine.is_available()` metodundan alınır; kapasite hesabında makine durumu yok sayılır (M4 için `is_available=False`, `theoretical=1800`, `effective=1710`, `shift_effective=1710`).

### 1.4 Yükleme ve Sınır Dönüşümleri (`loading.py`)
```python
load_records_dataframe(path: str) -> pd.DataFrame
records_to_dataframe(records: list) -> pd.DataFrame
dataframe_to_records(df: pd.DataFrame) -> list
```
- `load_records_dataframe`: `.csv` veya `.json` dosyasını tüm sütunları Pandas `"string"` dtype olacak şekilde yükler. Boş veya yalnızca boşluk içeren hücreler vektörel olarak `<NA>`'ya dönüştürülür; bozuk değerler (`"abc"`, `"2026-13-40"`) temizlik aşamasında yakalanmak üzere olduğu gibi korunur. 0 baytlık dosyalar `RECORD_COLUMNS` başlıklı boş `"string"` DataFrame döndürür. Eksik dosya, desteklenmeyen uzantı, hatalı CSV başlığı veya bozuk JSON `ValueError` (Türkçe mesaj) fırlatır.
- `records_to_dataframe`: `ProductionRecord` listesini Bölüm 3.2'deki temiz veri türlerine (`int64`, `datetime64`, `string`, `float64`) dönüştürür.
- `dataframe_to_records`: Tipli DataFrame'in her satırını MP3 `ProductionRecord.from_dict` ile doğrulayarak nesne listesine çevirir. (Plan Bölüm 3.1 uyarınca paket içinde satır döngüsüne izin verilen tek sınır dönüşüm noktasıdır.)

### 1.5 Ham Veri Üretim Hattı ve Hata Enjeksiyonu (`dataset.py`, `fault_injection.py`)
```python
build_clean_records(factory: dict, days: int = 120, seed: int = 42) -> list
write_raw_datasets(factory: dict, data_dir: str, days: int = 120, seed: int = 42) -> dict
inject_faults(clean_df: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]
save_dirty_records(dirty_df: pd.DataFrame, csv_path: str, json_path: str) -> None
```
- `build_clean_records`: `SimulationConfig.from_factory(factory, days=days, seed=seed)` → `simulate(config)` → `simulation_to_records(result, factory)` zincirini çalıştırır.
- `write_raw_datasets`: 600 kaydı MP3 `RecordStore.add_records` ile `raw_records_clean.csv` dosyasına yazar (`record_id` 1–600), ardından `inject_faults` ve `save_dirty_records` ile `raw_records_dirty.csv`, `raw_records_dirty.json` ve `fault_injection_log.csv` dosyalarını üretir.
- `inject_faults`: Yalnızca `np.random.default_rng(seed)` kullanır. İlk çekilişte `rng.choice(len(clean_df), size=66, replace=False)` ile 66 satır seçer ve `FAULT_PLAN` sırasıyla ardışık dilimlere ayırarak her satıra tek bir hata uygular. İkinci çekilişte kalan satırlardan `rng.choice(remaining, size=10, replace=False)` ile 10 satır seçip `record_id` 601–610 olarak sona ekler. Girdi `clean_df` asla değiştirilmez.
- `save_dirty_records`: JSON çıktısında geçerli tam/ondalıklı sayıları JSON sayı tipinde, bozuk metinleri (`"abc"`) string tipinde, `<NA>` değerleri `null` olarak yazar; böylece CSV ve JSON'dan `load_records_dataframe` ile okunan kirli veri birebir aynı DataFrame'i üretir.

### 1.6 Doğrulama ve Altın Değerler (Bölüm 7.1 & 7.2)
- **Ana tablolar (7.1):** M1–M5 teorik `[960, 1280, 480, 1800, 960]`, efektif `[816, 1152, 336, 1710, 768]`, vardiya efektif `[816, 576, 336, 1710, 768]`; MP1 tekil fonksiyonlarıyla `np.allclose` doğrulandı.
- **Temiz ham veri (7.2):** 600 satır (`M1: 120, M2: 240, M3: 120, M5: 120`), `planned_units = 322489`, `actual_units = 298071`, `downtime_hours = 238.0`; MP3 `RecordStore` ile hatasız okunmaktadır.
- **Kirli veri ve günlük (7.2):** 610 satır kirli veri, 76 satır hata günlüğü (66 bozuk + 10 `duplicate_key`). İlk 5 bozulan `record_id`: `[250, 576, 294, 40, 491]` (`missing_actual_units`); ilk 5 kopyalanan kaynak `record_id`: `[55, 201, 261, 176, 327]` (`record_id` 601–605).

### 1.7 Kişi B ve Kişi C İçin Teslim Arayüzleri ve Ana Projeye Taşınacak Parçalar
- **Kişi B (`cleaning.py`, `features.py`):** `schema.py` içinden `RECORD_COLUMNS`, `VALID_SHIFTS`, `KEY_FIELDS`, `ISSUE_ACTIONS`, `DERIVED_COLUMNS`, `CLEANING_LOG_COLUMNS` sabitlerini; `masters.py` içinden `build_machine_master` ve `build_product_master` fonksiyonlarını; `loading.py` içinden `load_records_dataframe`, `records_to_dataframe`, `dataframe_to_records` fonksiyonlarını doğrudan kullanabilir.
- **Kişi C (`kpi.py`, `questions.py`, `report.py`, `main.py`):** `schema.py` içinden `KPI_COLUMNS`, `RECORD_COLUMNS`, `DERIVED_COLUMNS` sabitlerini; `dataset.py` içinden `build_clean_records` ve `write_raw_datasets` fonksiyonlarını doğrudan çağırabilir.
- **Ana Projeye Taşınacaklar:** `schema.py` (PostgreSQL tablo şeması MP7, ML özellik sözleşmesi MP12–14), `masters.py` (optimizasyon ve çizelgeleme modelleri MP15–17 için vardiya bazlı efektif kapasite kaynağı), `loading.py` ve `fault_injection.py` (MP9 canlı veri üreticisi ve veri kalitesi test altyapısı).
