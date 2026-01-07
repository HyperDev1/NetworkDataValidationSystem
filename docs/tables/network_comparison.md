# network_comparison

Ana veri tablosu - GCS'deki Parquet dosyalarını BigQuery üzerinden sorgulayan external table.

## 📋 Genel Bilgi

| Özellik | Değer |
|---------|-------|
| **Tür** | External Table |
| **Kaynak** | GCS Parquet dosyaları |
| **Partition** | `dt` (DATE) - Hive partition |
| **Güncelleme** | Her sync sonrası otomatik |

## 📊 Şema

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `date` | DATE | Rapor tarihi (metrik günü) |
| `network` | STRING | Network adı (unity, ironsource, meta, vb.) |
| `platform` | STRING | Platform (android, ios) |
| `ad_type` | STRING | Reklam tipi (banner, interstitial, rewarded) |
| `application` | STRING | Uygulama adı |
| `max_revenue` | FLOAT64 | AppLovin MAX'ın raporladığı gelir (USD) |
| `max_impressions` | INT64 | AppLovin MAX'ın raporladığı impression |
| `max_ecpm` | FLOAT64 | AppLovin MAX eCPM |
| `network_revenue` | FLOAT64 | Network'ün kendi raporladığı gelir (USD) |
| `network_impressions` | INT64 | Network'ün kendi raporladığı impression |
| `network_ecpm` | FLOAT64 | Network eCPM |
| `rev_delta_pct` | FLOAT64 | Gelir farkı yüzdesi ((network-max)/max * 100) |
| `imp_delta_pct` | FLOAT64 | Impression farkı yüzdesi |
| `ecpm_delta_pct` | FLOAT64 | eCPM farkı yüzdesi |
| `fetched_at` | TIMESTAMP | Verinin çekildiği zaman |
| `dt` | DATE | Hive partition kolonu |

## 🔍 Örnek Sorgular

### Son 7 günün network bazlı özeti
```sql
SELECT 
    date,
    network,
    SUM(max_revenue) as max_revenue,
    SUM(network_revenue) as network_revenue,
    ROUND((SUM(network_revenue) - SUM(max_revenue)) / NULLIF(SUM(max_revenue), 0) * 100, 2) as delta_pct
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY date, network
ORDER BY date DESC, network
```

### Platform ve ad_type bazlı analiz
```sql
SELECT 
    network,
    platform,
    ad_type,
    SUM(max_revenue) as max_revenue,
    SUM(network_revenue) as network_revenue,
    SUM(max_impressions) as max_impressions,
    SUM(network_impressions) as network_impressions
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY network, platform, ad_type
ORDER BY max_revenue DESC
```

### Büyük tutarsızlıklar (>10% fark)
```sql
SELECT *
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
WHERE ABS(rev_delta_pct) > 10
  AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY ABS(rev_delta_pct) DESC
```

---

## 📈 Looker Kullanımı

### 1. Data Source Oluşturma

1. Looker Studio'da **Add Data** → **BigQuery** seç
2. Project: `gen-lang-client-0468554395`
3. Dataset: `ad_network_analytics`
4. Table: `network_comparison`

### 2. Önerilen Grafikler

#### A) Günlük Gelir Karşılaştırma (Time Series)

| Ayar | Değer |
|------|-------|
| **Chart Type** | Time Series |
| **Dimension** | `date` |
| **Metrics** | `SUM(max_revenue)`, `SUM(network_revenue)` |
| **Breakdown** | `network` |

**Kullanım:** Günlük bazda MAX vs Network gelir trendini gösterir.

#### B) Network Bazlı Delta Heatmap

| Ayar | Değer |
|------|-------|
| **Chart Type** | Pivot Table / Heatmap |
| **Rows** | `network` |
| **Columns** | `date` |
| **Metric** | `AVG(rev_delta_pct)` |
| **Conditional Formatting** | Kırmızı: >5%, Yeşil: <-5% |

**Kullanım:** Hangi network'ün hangi günlerde tutarsızlık gösterdiğini gösterir.

#### C) Platform & Ad Type Breakdown (Stacked Bar)

| Ayar | Değer |
|------|-------|
| **Chart Type** | Stacked Bar |
| **Dimension** | `network` |
| **Breakdown** | `platform` veya `ad_type` |
| **Metric** | `SUM(max_revenue)` |

**Kullanım:** Her network'ün platform/ad_type dağılımını gösterir.

#### D) Discrepancy Alert Table

| Ayar | Değer |
|------|-------|
| **Chart Type** | Table |
| **Dimensions** | `date`, `network`, `platform`, `ad_type` |
| **Metrics** | `max_revenue`, `network_revenue`, `rev_delta_pct` |
| **Filter** | `ABS(rev_delta_pct) > 5` |
| **Sort** | `ABS(rev_delta_pct)` DESC |

**Kullanım:** Dikkat gerektiren tutarsızlıkları listeler.

### 3. Calculated Fields (Looker'da Oluştur)

```sql
-- Absolute Delta
ABS(rev_delta_pct)

-- Delta Category
CASE 
    WHEN ABS(rev_delta_pct) > 10 THEN "Critical"
    WHEN ABS(rev_delta_pct) > 5 THEN "Warning"
    ELSE "OK"
END

-- Revenue Difference (USD)
network_revenue - max_revenue
```

### 4. Filtreler

| Filtre | Kullanım |
|--------|----------|
| **Date Range** | Son 7/30/90 gün seçimi |
| **Network** | Belirli network'lere odaklanma |
| **Platform** | android/ios filtreleme |
| **Ad Type** | banner/interstitial/rewarded |
| **Delta Threshold** | Sadece >X% farkları göster |

---

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Partition Kullanımı:** Büyük tarih aralıklarında `WHERE date >= ...` kullanın, aksi halde tüm GCS taranır.

2. **NULL Değerler:** Bazı network'ler bazı metrikler raporlamayabilir. `NULLIF` veya `COALESCE` kullanın.

3. **Delta Yorumlama:**
   - Pozitif delta: Network daha fazla raporluyor
   - Negatif delta: MAX daha fazla raporluyor
   - %5'e kadar normal kabul edilebilir (timing farkları)
