# Sentetik Veri Üretim Kuralları (Mini Proje 4)

Bu belge, `capacity_simulation/generation.py` içindeki `simulate()` fonksiyonunun sentetik üretim verisini **hangi kurallarla** ürettiğini sade bir dille açıklar (proje planı Bölüm 3.2–3.4). Amaç, ana projede gerçek veri yokken kullanılacak verinin nereden geldiğini herkesin anlayabilmesi ve aynı veriyi yeniden üretebilmesidir.

---

## 1. Ne Üretiliyor?

- Simülasyon **makine–gün** düzeyindedir. Her değer, bir makinenin bir günkü toplamıdır.
- Tüm matrisler `(M, D)` şeklindedir: `axis=0` makine, `axis=1` gün (M = makine sayısı, D = gün sayısı).
- Makineler MP2 örnek fabrikasından gelir; yalnızca üretime uygun (`is_available()`) makineler alınır. Varsayılan örnek: **M1, M2, M3, M5** (M4 bozuk), **30 gün**, **tohum 42** → 120 makine–gün.
- Tarih alanı yoktur; gün `i` için tarih `start_date + i gün` olarak yalnızca dışa aktarımda hesaplanır (varsayılan `start_date = 2026-10-01`).

| Dizi | Tür ve şekil | Birim / Kural |
| :--- | :--- | :--- |
| `theoretical_capacity` | float64 `(M,)` | adet/gün |
| `efficiency_pct` | float64 `(M, D)` | yüzde, makinenin `[efficiency_min_pct, efficiency_max_pct]` aralığında |
| `effective_capacity` | float64 `(M, D)` | adet/gün |
| `planned_units` | int64 `(M, D)` | adet, en az 1 |
| `downtime_hours` | float64 `(M, D)` | saat, 0 veya 0,25'in katı, en fazla makinenin `working_hours` değeri |
| `actual_units` | int64 `(M, D)` | adet, en az 0 |

## 2. Girdiler ve Aralıklar

| Kural | Değer | Sabit (`models.py`) |
| :--- | :--- | :--- |
| Günlük verimlilik aralığı | `base − 10` ile `min(100, base + 5)` arası, düzgün (uniform) | `EFFICIENCY_DOWN_PCT`, `EFFICIENCY_UP_PCT` |
| Yük oranı (load factor) | 0,80 – 1,00, düzgün | `LOAD_FACTOR_RANGE` |
| Duruş olasılığı | %30 (her makine–gün için bağımsız) | `DOWNTIME_PROBABILITY` |
| Duruş süresi | 0,25 – 3,0 saat, çeyrek saate yuvarlanır | `DOWNTIME_HOURS_RANGE`, `DOWNTIME_STEP_HOURS` |
| Performans oranı | 0,90 – 1,05, düzgün | `PERFORMANCE_FACTOR_RANGE` |

Bu sayılar MP3 `generate_records` ile aynıdır. MP3 `random.Random`, MP4 NumPy kullandığı için **kurallar aynıdır ama çıkan sayılar aynı değildir**.

Örnek fabrikada türetilen aralıklar:

| Makine | working_hours | cycle_time_sec | base | min | max | theoretical_capacity |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 | 8 | 30 | 85 | 75 | 90 | 960 |
| M2 | 16 | 45 | 90 | 80 | 95 | 1280 |
| M3 | 8 | 60 | 70 | 60 | 75 | 480 |
| M5 | 8 | 30 | 80 | 70 | 85 | 960 |

## 3. Rastgele Sayı Çizim Sırası (Tekrarlanabilirlik Sözleşmesi)

`simulate(config)` içinde **tek bir** üreteç oluşturulur: `rng = np.random.default_rng(config.seed)`. Ardından çizimler **tam bu sırayla ve tam bu şekille** yapılır:

| Sıra | Çağrı | Üretilen | Fonksiyon |
| :---: | :--- | :--- | :--- |
| 1 | `rng.uniform(low[:, None], high[:, None], size=(M, D))` | `efficiency_pct` | `generate_efficiency_matrix` |
| 2 | `rng.uniform(0.80, 1.00, size=(M, D))` | yük oranı | `generate_load_factor_matrix` |
| 3 | `rng.random((M, D))` | duruş var mı? (`< 0.30` ise var) | `generate_downtime_matrix` |
| 4 | `rng.uniform(0.25, 3.0, size=(M, D))` | duruş süresi (`round(x × 4) / 4`) | `generate_downtime_matrix` |
| 5 | `rng.uniform(0.90, 1.05, size=(M, D))` | performans oranı | `generate_performance_factor_matrix` |

Önemli ayrıntılar:

- Her çizim **tam `(M, D)` matristir**; makine başına ayrı çizim veya döngü yoktur.
- Çizim 4, duruş olmayan hücreler için de üretilir (sonra `where` ile 0 yapılır). Yalnızca duruşlu hücreler için çizim yapmak akışı kaydırır ve sonraki performans oranlarını değiştirir.
- `np.random.seed` ve küresel `np.random.*` çağrıları **kullanılmaz**; üreteç fonksiyonlara parametre olarak geçirilir.

### Tohum ve çizim sırası neden önemli?

NumPy üreteci, aynı tohumdan her zaman aynı sayı dizisini verir. Bu dizi sırayla tüketilir: önce `M × D` verimlilik sayısı, sonra `M × D` yük oranı vb. Bu yüzden:

- **Aynı tohum + aynı yapılandırma = birebir aynı sonuç.** Testler, hata ayıklama ve ekip içi karşılaştırma bu sayede mümkündür (`simulate` saf bir fonksiyondur).
- Çizim **sırası** değişirse (ör. performans oranı yük oranından önce çekilirse) aynı sayılar farklı anlamlara atanır.
- Çizim **şekli** değişirse (ör. `(D, M)` veya makine başına ayrı çizim) sayılar farklı hücrelere düşer.
- **NumPy sürümü** değişirse üretecin algoritması değişebilir. Referans değerler **NumPy 2.4.4** ile üretilmiştir; sürüm `requirements.txt` dosyasında sabitlenir.

Bu değişikliklerin hepsi programı çalışır hâlde bırakır ama sonuçları sessizce değiştirir. Bunu yakalamak için Bölüm 7.3 altın değer testi (`tests/test_simulation.py`) zorunludur. Test kırılırsa sayılar değiştirilmez; neden değiştiği ekipçe incelenir.

## 4. Formüller (Vektörel)

Hesaplama sırası: verimlilik → efektif kapasite → yük oranı → planlanan → duruş → performans oranı → gerçekleşen.

```text
theoretical_capacity = working_hours × 3600 / cycle_time_sec                       (M,)
effective_capacity   = theoretical_capacity[:, None] × efficiency_pct / 100         (M, D)
planned_units        = rint(effective_capacity × load_factor)                        (M, D) int64
downtime_hours       = where(r < 0.30, round(x × 4) / 4, 0), working_hours[:, None] ile sınırlı
actual_units         = max(0, rint(planned_units × performance_factor
                                   × (1 − downtime_hours / working_hours[:, None])))  (M, D) int64
```

- Kapasite formülleri yalnızca `capacity.py` içindedir (Kişi A); `generation.py` bu fonksiyonları çağırır.
- Yuvarlama `np.rint` ile yapılır: en yakın tam sayıya, tam yarıda **çift sayıya** (Python `round` ile aynı; ör. 2,5 → 2, 3,5 → 4).
- Herhangi bir hücrede `planned_units < 1` olursa `ValueError` verilir (ör. çok büyük `cycle_time_sec`).
- Duruş, makinenin çalışma süresine eşitse o gün `actual_units = 0` olur.
- Girdi dizileri değiştirilmez; her fonksiyon yeni dizi döndürür.

### Elle doğrulanmış örnek (Bölüm 7.2)

M1 (8 saat, 30 sn) ve M2 (16 saat, 45 sn), 3 gün:

| | M1 (gün 1, 2, 3) | M2 (gün 1, 2, 3) |
| :--- | :--- | :--- |
| efficiency_pct | 85, 80, 90 | 90, 95, 100 |
| load_factor | 1,0, 1,0, 0,5 | 0,5, 1,0, 1,0 |
| performance_factor | 1,0, 0,9, 1,0 | 1,0, 1,0, 1,0 |
| downtime_hours | 0, 0, 2,0 | 0,5, 0, 0 |
| **effective_capacity** | 816, 768, 864 | 1152, 1216, 1280 |
| **planned_units** | 816, 768, 432 | 576, 1216, 1280 |
| **actual_units** | 816, 691, 324 | 558, 1216, 1280 |

Örn. M1 gün 2: 768 × 0,9 = 691,2 → 691; M1 gün 3: 432 × (1 − 2/8) = 324; M2 gün 1: 576 × (1 − 0,5/16) = 558.

## 5. KPI Tanımları

- `production_gap = actual − planned` (pozitif fazla üretim, negatif açık; MP1/MP3 ile aynı işaret)
- `attainment_pct = actual / planned × 100`
- `availability_pct = (toplam çalışma saati − toplam duruş) / toplam çalışma saati × 100`, toplam çalışma saati = `sum(working_hours) × days`
- Standart sapma `ddof=0` (popülasyon) ile hesaplanır.

Toplam KPI'lar ve özet sözlüğü `stats.py` (Kişi C) tarafından MP3 `analysis.py` fonksiyonlarıyla hesaplanır; yuvarlama yalnızca rapor aşamasındadır.

## 6. Referans (Altın) Değerler — Tohum 42, Örnek Fabrika, 30 Gün, NumPy 2.4.4

| Büyüklük | Değer |
| :--- | :--- |
| Matris şekli | (4, 30) |
| Toplam planlanan / gerçekleşen | 80449 / 73774 |
| Üretim farkı | −6675 |
| Plan gerçekleşme | %91,70 |
| Toplam duruş / duruşlu makine–gün | 65,25 saat / 37 |
| Kullanılabilirlik | %94,56 (toplam çalışma saati 1200) |
| En küçük planlanan | 233 |
| Verimlilik ortalaması | 78,73 |
| Efektif kapasite ort., std, min, maks | 745,57, 286,24, 289,64, 1209,76 |
| Efektif kapasite makine ortalamaları | 800,52, 1116,25, 320,03, 745,49 |

Bu değerler `tests/test_simulation.py` ile her çalıştırmada doğrulanır.
