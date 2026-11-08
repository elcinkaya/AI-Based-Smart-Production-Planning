# Mini Proje 5 – Modül Notları (Kişi B Bölümü)

> **Birleştirme Notu (Kişi C için):** Bu dosya, ortak `docs/module_notes.md` içinde yer alacak **"2. Temizlik ve Türetilmiş Değişkenler (Kişi B)"** bölümüdür. Ayrıca kolaylık olması için `docs/module_notes.md` dosyası da Kişi A (Bölüm 1) ve Kişi B (Bölüm 2) notlarını içerecek şekilde hazırlanmıştır; Kişi C doğrudan 3. bölümü ekleyebilir.

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
