# Mini Proje 5 – Modül Notları

Bu belge, **Mini Proje 5: Pandas ile Üretim Verisi Analizi** kapsamında geliştirilen modüllerin teknik sözleşmelerini, doğrulama sonuçlarını ve ana projedeki (23 mini proje yol haritası) yeniden kullanım noktalarını içerir.

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

---

## 2. Temizlik ve Türetilmiş Değişkenler (Kişi B)

### 2.1 Sorumluluk Kapsamı
- `production_analysis/cleaning.py`: Vektörel veri doğrulama, hatalı kayıt temizliği, eksik `downtime_hours` doldurma, mükerrer anahtar (`duplicate_key`) eleme ve temizlik özeti (`clean_records`, `summarize_cleaning`).
- `production_analysis/features.py`: Makine ve ürün ana tablolarıyla birleştirme, kayıt düzeyi türetilmiş değişkenlerin hesaplanması, eksiksiz günlük zaman serisi ve Pazartesi başlangıçlı haftalık özet üretimi (`add_derived_columns`, `build_daily_series`, `build_weekly_summary`).
- `tests/test_cleaning.py`: Bölüm 7.3 altın değerleri (610 -> 546 satır, 64 silinen, 12 doldurulan, 76 günlük satırı), değişmezler, 10 sınır durumu ve Bölüm 7.7 hata testleri.
- `tests/test_features.py`: Bölüm 7.4 (MP3'ün 8 sabit kaydıyla türetilmiş sütunlar, günlük/haftalık seriler), Bölüm 7.5 tam hat türetilmiş değişken/zaman serisi kontrolleri ve Bölüm 7.7 hata testleri.
- `docs/data_quality_rules.md`: Veri üretim, kontrollü hata enjeksiyonu ve Bölüm 3.3 temizlik kurallarının gerekçeli dokümantasyonu.

### 2.2 Veri Temizleme ve Günlük Sözleşmesi (`cleaning.py`)
```python
clean_records(
    raw_df: pd.DataFrame,
    machine_master: pd.DataFrame,
    product_master: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]

summarize_cleaning(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    cleaning_log_df: pd.DataFrame,
) -> dict
```
- **5 Adımlı İşlem Sırası (Bölüm 3.3):**
  1. Boş ve yalnızca boşluktan oluşan hücreler (`""`, `"   "`) vektörel olarak `<NA>`'ya çevrilir (dolu metinler kırpılmaz, sessiz düzeltme yapılmaz).
  2. `pd.to_datetime(..., format='%Y-%m-%d', errors='coerce')` + sıkı ISO `YYYY-MM-DD` regex kontrolü, `pd.to_numeric(..., errors='coerce')` ve `.isin(...)` ile 10 temel sorun kodu için boolean maskeler üretilir. Eksik (`<NA>`) değerler yalnızca `missing_*` olarak işaretlenir; `invalid_*` veya `unknown_*` ile çakışmaz.
  3. En az bir `'dropped'` sorunu olan satırlar çıkarılır. Aynı satırda birden fazla sorun varsa her biri `cleaning_log_df` içine ayrı satır olarak yazılır (`record_id` ve Bölüm 3.3 tablo sırasına göre sıralı), ancak satır yalnızca bir kez silinir.
  4. Kalan satırlarda eksik `downtime_hours` değerleri `0.0` ile doldurulur (MP3 varsayılanı; tek belgelenmiş düzeltme).
  5. Kalan geçerli satırlar `record_id` artan sıraya dizilir ve `(production_date, shift, machine_id)` üzerinde `duplicated(keep='first')` ile en küçük `record_id` korunarak mükerrer kayıtlar (`duplicate_key`) silinip günlüğe eklenir.
- **Çıktı Tipleri (`clean_df`):** `record_id`, `planned_units`, `actual_units` -> `int64`; `production_date` -> `datetime64`; `shift`, `machine_id`, `product_code` -> `string`; `downtime_hours` -> `float64`. Sütun sırası `RECORD_COLUMNS`, indeks `0..n-1`.
- **Özet Sözlüğü (`summarize_cleaning`):** `{'raw_row_count', 'clean_row_count', 'dropped_row_count', 'filled_row_count', 'issue_counts'}` anahtarlarını döndürür.

### 2.3 Türetilmiş Değişkenler ve Zaman Serileri (`features.py`)
```python
add_derived_columns(
    clean_df: pd.DataFrame,
    machine_master: pd.DataFrame,
    product_master: pd.DataFrame,
) -> pd.DataFrame

build_daily_series(analysis_df: pd.DataFrame) -> pd.DataFrame
build_weekly_summary(analysis_df: pd.DataFrame) -> pd.DataFrame
```
- **Ana Tablo Birleştirme (`add_derived_columns`):** `machine_master[['machine_id', 'line_id', 'shift_effective_capacity']]` ve `product_master[['product_code', 'priority']]` tabloları `merge(..., how='left', validate='many_to_one')` ile birleştirilir. Eşleşmeyen `machine_id` veya `product_code` varsa Türkçe mesajlı `ValueError` fırlatılır. Kapasite formülü tekrar yazılmaz; doğrudan ana tablodaki `shift_effective_capacity` kullanılır.
- **Türetilmiş Sütunlar (`DERIVED_COLUMNS`):**
  - `line_id` (`string`), `priority` (`int64`), `shift_effective_capacity` (`float64`)
  - `production_gap = actual_units - planned_units` (`int64`)
  - `attainment_pct = actual_units / planned_units * 100.0` (`float64`)
  - `availability_pct = (8.0 - downtime_hours) / 8.0 * 100.0` (`float64`)
  - `capacity_utilization_pct = actual_units / shift_effective_capacity * 100.0` (`float64`)
  - `plan_met = actual_units >= planned_units` (`bool`)
  - `has_downtime = downtime_hours > 0` (`bool`)
  - `weekday = production_date.dt.dayofweek` (`int64`, `0 = Pazartesi ... 6 = Pazar`)
  - `week_start = production_date.dt.normalize() - pd.to_timedelta(weekday, unit='D')` (`datetime64`)
- **Günlük Seri (`build_daily_series`):** İndeks `production_date` (`min`..`max` arası `freq='D'` eksiksiz takvim aralığı). Sütunlar (`DAILY_SERIES_COLUMNS`): `record_count`, `total_planned_units`, `total_actual_units`, `total_downtime_hours`, `production_gap`, `attainment_pct` (kayıtsız günde `NaN`), `actual_units_ma7` (`rolling(7, min_periods=7).mean()`), `is_missing_day` (`record_count == 0`).
- **Haftalık Özet (`build_weekly_summary`):** İndeks `week_start` (Pazartesi). Sütunlar (`WEEKLY_SUMMARY_COLUMNS`): `day_count` (o haftada kaydı olan farklı gün sayısı), `record_count`, `total_planned_units`, `total_actual_units`, `total_downtime_hours`, `production_gap`, `attainment_pct`, `is_complete_week` (`day_count == 7`).

### 2.4 Doğrulama ve Altın Değerler (Bölüm 7.3, 7.4 & 7.5)
- **Bölüm 7.3 (610 satırlık kirli veri temizliği):** `raw_row_count = 610`, `clean_row_count = 546`, `dropped_row_count = 64`, `filled_row_count = 12`, `len(cleaning_log_df) = 76`. `issue_counts` altın değerleriyle ve `fault_injection_log.csv` ile birebir eşleşmektedir. 546 satırın tamamı `dataframe_to_records` (MP3 doğrulaması) kontrolünden hatasız geçmektedir.
- **Bölüm 7.4 (MP3 8 sabit kayıt):** Toplamlar (`4510`, `4366`, `-144`, `%96,81`, `5,0 saat`, `%92,19`), genel ve makine bazlı kapasite kullanım oranları (`%94,75`; M1 `%93,79`, M2 `%97,22`, M3 `%94,25`), `weekday` (`3, 4, 5`), `week_start` (`2026-09-28`), günlük seri (3 satır ve 2 Ekim çıkarıldığında eksik gün davranışı) ve haftalık özet (`day_count=3`, `record_count=8`, `is_complete_week=False`) birebir doğrulandı.
  - *Not:* Word belgesi Bölüm 7.4 tablosundaki "Kayıt 2, 4, 7 tekil yüzdeleri ve M1/M2/M3 `attainment_pct_std`" satırları, depodaki `data/test_records.csv` dosyasının sayısal değerleriyle (ör. Kayıt 2'de `760 / 800 = %95,00` iken tabloda `%105,26` yazması) matematiksel olarak uyuşmamaktadır. Kural gereği altın değerler değiştirilmemiş; bu değerleri birebir koruyan test `unittest.skip` ile belgelenmiş ve formülün doğruluğu tanılayıcı testle (`TestPlanGoldenFormulaReproduction`) kanıtlanmıştır.
- **Bölüm 7.5 (546 temiz satır üzerinde tam hat):** Toplam planlanan `293032`, gerçekleşen `270519`, fark `-22513`, duruş `223,375`, kapasite kullanımı `%80,72`, duruşlu kayıt `159`, `attainment_pct_std (ddof=0) = 10,12`; günlük seri `120` gün (eksik gün yok; `5: 76, 4: 36, 3: 6, 2: 2`), haftalık özet `18` hafta (`16` tam hafta, en büyük açık `2026-10-19` haftasında `-1720`) birebir doğrulandı.

### 2.5 Kişi C İçin Teslim Arayüzleri ve Ana Projeye Taşınacak Parçalar
- **Kişi C (`kpi.py`, `questions.py`, `report.py`, `main.py`):**
  - `from production_analysis.cleaning import clean_records, summarize_cleaning`
  - `from production_analysis.features import add_derived_columns, build_daily_series, build_weekly_summary, DAILY_SERIES_COLUMNS, WEEKLY_SUMMARY_COLUMNS`
  - `add_derived_columns` çıktısı olan `analysis_df`, `calculate_kpi_table`, `summarize_kpi` ve `answer_business_questions` fonksiyonlarının doğrudan girdisidir.
  - `build_daily_series` ve `build_weekly_summary` çıktıları `save_analysis_outputs` ve `q5` (tam haftalar içinde en büyük üretim açığı) için doğrudan kullanılabilir.
- **Ana Projeye Taşınacaklar:**
  - `cleaning.py`: MP7 PostgreSQL veri yükleme öncesi temizlik katmanı ve MP9 canlı veri akışı doğrulama filtresi.
  - `features.py`: MP6 Dashboard (`daily_series.csv`, `weekly_summary`), MP10 İstatistiksel EDA (`analysis_dataset.csv`), MP11 Talep/Üretim Tahmini (`actual_units_ma7`, `is_missing_day`) ve MP12–14 Makine Öğrenmesi modelleri (`shift_effective_capacity`, `priority`, `weekday`, `has_downtime`) için temel özellik mühendisliği (feature engineering) modülüdür.

---

## 3. KPI Tabloları, İşletme Soruları, Raporlama ve Entegrasyon (Kişi C)

### 3.1 Sorumluluk Kapsamı
- `production_analysis/kpi.py`: Grup bazında vektörel toplulaştırma, KPI tabloları, genel KPI özeti ve MP3 rapor uyumluluk dönüşümü (`calculate_kpi_table`, `summarize_kpi`, `kpi_table_to_group_summaries`, `build_kpi_tables`, `calculate_group_date_ranges`).
- `production_analysis/questions.py`: Bölüm 7.5'teki yedi işletme sorusunun (`q1`–`q7`) gerçek veri üzerinden dinamik yanıtlanması (`answer_business_questions`).
- `production_analysis/report.py`: MP3 `build_summary_report` bloğunu içeren Türkçe çerçeveli analiz raporu ve Bölüm 4'teki tüm analiz CSV çıktılarının kaydedilmesi (`build_analysis_report`, `print_analysis_report`, `save_analysis_outputs`).
- `production_analysis/__init__.py`: Üç ekip üyesinin modüllerini tek paket arayüzünde dışa açan ortak bildirim dosyası.
- `main.py`: MP1 `get_number` ile çalışan 7 seçenekli Türkçe konsol menüsü ve uçtan uca veri hattı (`1 → 5`).
- `tests/test_kpi.py`, `tests/test_questions.py`, `tests/test_integration.py`: Bölüm 7.4, 7.5, 7.6 (MP1/MP3/MP4 8 uyum senaryosu) ve 7.7 testleri.
- Teslim belgeleri ve çıktılar: `README.md`, `requirements.txt`, `docs/screenshot.png`, `docs/sample_report.txt` ve `data/` altındaki analiz CSV dosyaları.

### 3.2 KPI Hesaplama ve Toplulaştırma Sözleşmesi (`kpi.py`)
```python
calculate_kpi_table(analysis_df: pd.DataFrame, group_by=None) -> pd.DataFrame
summarize_kpi(analysis_df: pd.DataFrame) -> dict
kpi_table_to_group_summaries(kpi_table: pd.DataFrame, date_ranges=None) -> dict
build_kpi_tables(analysis_df: pd.DataFrame) -> dict
```
- **Grup Toplamları İlkesi (Bölüm 3.4):** Yüzde KPI'ları (`attainment_pct`, `availability_pct`, `capacity_utilization_pct`) hiçbir zaman tekil kayıt yüzdelerinin ortalamasıyla hesaplanmaz; `groupby(...).agg(...)` (named aggregation) ile elde edilen grup toplamları üzerinden vektörel olarak hesaplanır:
  - `production_gap = total_actual_units - total_planned_units`
  - `attainment_pct = total_actual_units / total_planned_units * 100.0`
  - `availability_pct = (record_count * 8.0 - total_downtime_hours) / (record_count * 8.0) * 100.0`
  - `capacity_utilization_pct = total_actual_units / sum(shift_effective_capacity) * 100.0`
  - `downtime_event_count`: `downtime_hours > 0` olan kayıtların grup toplamı
  - `attainment_pct_std`: kayıt düzeyindeki `attainment_pct` sütununun popülasyon standart sapması (`ddof=0` açıkça belirtilir)
  - `plan_met = total_actual_units >= total_planned_units` ve MP3 ile birebir aynı Türkçe `status_message` metinleri.
- **Sütun Sözleşmesi (`KPI_COLUMNS`):** `['record_count', 'total_planned_units', 'total_actual_units', 'production_gap', 'attainment_pct', 'total_downtime_hours', 'availability_pct', 'capacity_utilization_pct', 'downtime_event_count', 'attainment_pct_std', 'plan_met', 'status_message']`.
- **MP3 Köprüsü (`kpi_table_to_group_summaries`):** Herhangi bir KPI tablosunu MP3 `summarize_by` sözlük biçimine dönüştürerek MP3 `build_summary_report` fonksiyonunun doğrudan yeniden kullanılmasını sağlar.

### 3.3 İşletme Soruları (`questions.py`)
```python
answer_business_questions(analysis_df: pd.DataFrame) -> dict
```
- `q1`–`q7` anahtarlarının her biri `{'question': <Türkçe soru metni>, 'answer': <dict>}` yapısındadır. Hiçbir değer sabit kodlanmamıştır:
  - `q1` (en düşük plan gerçekleşme makinesi): **M3 (%90,23)**
  - `q2` (en düşük kullanılabilirlik vardiyası): **morning (%94,51)** vs afternoon (%96,43)
  - `q3` (toplam vs kayıt başına duruş): Toplamda **P-B (83,875 saat)**, kayıt başında **P-C (0,4956 saat)** (P-A 0,3795, P-B 0,3938)
  - `q4` (planı karşılamayan kayıt oranı): Genel **%77,84 (425 / 546)**; en yüksek **M3 (%85,32)** (kayıt sayısında M2 168 adet ile önde olsa da oranda M3 en yüksektir)
  - `q5` (tam haftalar içinde en büyük üretim açığı): **2026-10-19 haftası (-1720 adet, 16 tam hafta içinde)**
  - `q6` (en yüksek kapasite kullanım oranı): **M2 (%82,79)** (M1 %80,68, M5 %79,13, M3 %77,32)
  - `q7` (duruşlu vs duruşsuz kayıtların ortalama gerçekleşme farkı): 159 duruşlu kayıtta **%80,40**, 387 duruşsuz kayıtta **%97,05**, fark **16,65 puan**.

### 3.4 Raporlama ve Dosya Çıktıları (`report.py`)
```python
build_analysis_report(cleaning_summary: dict, summary: dict, kpi_tables: dict, answers: dict) -> str
print_analysis_report(cleaning_summary: dict, summary: dict, kpi_tables: dict, answers: dict) -> None
save_analysis_outputs(data_dir: str, clean_df, cleaning_log_df, analysis_df, kpi_tables: dict, daily_series, weekly_summary) -> list[str]
```
- Yuvarlama yalnızca `report.py` içinde görüntüleme aşamasında yapılır; DataFrame'ler ve CSV dosyaları yuvarlanmamış tam hassasiyetli değerleri taşır.
- `save_analysis_outputs` fonksiyonu `clean_records.csv` dosyasını `dataframe_to_records` + MP3 `save_records_csv` ile yazar; böylece dosya MP3 `RecordStore` tarafından sıfır veri kaybıyla okunabilir.
- Üretilen 10 analiz CSV dosyası: `clean_records.csv`, `cleaning_log.csv`, `analysis_dataset.csv`, `kpi_by_machine.csv`, `kpi_by_product.csv`, `kpi_by_shift.csv`, `kpi_by_day.csv`, `kpi_by_week.csv`, `daily_series.csv`, `weekly_summary.csv`.

### 3.5 Sonraki Mini Projelere (MP6–MP23) Aktarılacak Bileşenler
| Hedef Mini Proje | MP5'ten Aktarılan Modül / Dosya | Kullanım Amacı |
|---|---|---|
| **MP6 – Üretim Dashboard** | `kpi_by_*.csv`, `daily_series.csv`, `weekly_summary.csv`, `build_kpi_tables` | Makine/ürün/vardiya KPI grafiklerinin ve 7 günlük hareketli ortalama serisinin görselleştirilmesi |
| **MP7 – PostgreSQL Şeması** | `schema.py`, `masters.py`, `clean_records.csv`, `cleaning_log.csv` | İlişkisel veritabanı tablo şemaları ve `(production_date, shift, machine_id)` benzersizlik kısıtı |
| **MP8 – İleri SQL Analizi** | `kpi.py` altın değerleri (`293032`, `270519`, `-22513`, `%92,32`) | SQL pencere ve toplulaştırma sorgularının referans doğrulaması |
| **MP9 – Canlı Veri Üreticisi** | `fault_injection.py`, `cleaning.py`, `docs/data_quality_rules.md` | Akan üretim verisinde hata enjeksiyonu ve gerçek zamanlı temizlik filtresi |
| **MP10 – İstatistiksel EDA** | `analysis_dataset.csv`, `attainment_pct_std` (`ddof=0`) | Dağılım, korelasyon ve hipotez testleri için hazır temiz veri seti |
| **MP11 – Zaman Serisi Tahmini** | `build_daily_series`, `actual_units_ma7`, `is_missing_day` | Eksiksiz günlük frekanslı (`freq='D'`) talep/üretim tahmin serisi |
| **MP12–14 – Makine Öğrenmesi** | `add_derived_columns` (`shift_effective_capacity`, `priority`, `weekday`, `has_downtime`) | Kestirimci bakım ve verimlilik tahmin modelleri için özellik matrisi |
| **MP15–17 – Optimizasyon** | `build_machine_master`, `build_product_master`, KPI taban çizgileri | Kapasite kısıtlı üretim çizelgeleme ve yeniden planlama parametreleri |
| **MP19, MP21 – Streamlit & FastAPI** | `calculate_kpi_table`, `summarize_kpi`, `answer_business_questions` | Karar destek arayüzü ve REST API uç noktalarının doğrudan servis katmanı |
| **MP23 – Tam Sistem Entegrasyonu** | `production_analysis` paketi (`__init__.py`) | Ortak veri hazırlama, temizlik ve KPI hesaplama çekirdek paketi |

