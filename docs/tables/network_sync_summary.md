# network_sync_summary

Her network için özet senkronizasyon durumu ve toplam metrikler. Network bazlı performans karşılaştırması için kullanılır.

## 📋 Genel Bilgi

| Özellik | Değer |
|---------|-------|
| **Tür** | View |
| **Kaynak** | `network_comparison` tablosundan türetilir |
| **Satır Sayısı** | Network sayısı kadar (örn: 12) |
| **Güncelleme** | Real-time (view olduğu için) |

## 📊 Şema

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `network` | STRING | Network adı |
| `record_count` | INT64 | Bu network için toplam kayıt sayısı |
| `last_report_date` | DATE | Bu network için en son rapor tarihi |
| `last_sync_time` | TIMESTAMP | Bu network için son sync zamanı |
| `last_report_date_str` | STRING | Formatlanmış son rapor tarihi |
| `last_sync_str` | STRING | Formatlanmış son sync zamanı |
| `total_max_revenue` | FLOAT64 | Bu network'ün toplam MAX geliri |
| `total_network_revenue` | FLOAT64 | Bu network'ün toplam kendi raporladığı gelir |
| `overall_rev_delta_pct` | FLOAT64 | Genel gelir farkı yüzdesi |

## 🔍 Örnek Sorgular

### Tüm network'lerin özeti
```sql
SELECT * 
FROM `gen-lang-client-0468554395.ad_network_analytics.network_sync_summary`
ORDER BY total_max_revenue DESC
```

### En yüksek tutarsızlığa sahip network'ler
```sql
SELECT 
    network,
    total_max_revenue,
    total_network_revenue,
    overall_rev_delta_pct
FROM `gen-lang-client-0468554395.ad_network_analytics.network_sync_summary`
WHERE ABS(overall_rev_delta_pct) > 5
ORDER BY ABS(overall_rev_delta_pct) DESC
```

### Sync durumu kontrolü
```sql
SELECT 
    network,
    last_report_date,
    DATE_DIFF(CURRENT_DATE(), last_report_date, DAY) as days_behind,
    last_sync_time
FROM `gen-lang-client-0468554395.ad_network_analytics.network_sync_summary`
ORDER BY days_behind DESC
```

---

## 📈 Looker Kullanımı

### 1. Data Source Oluşturma

1. Looker Studio'da **Add Data** → **BigQuery** seç
2. Project: `gen-lang-client-0468554395`
3. Dataset: `ad_network_analytics`
4. Table: `network_sync_summary`

### 2. Önerilen Grafikler

#### A) Network Gelir Karşılaştırma (Bar Chart)

| Ayar | Değer |
|------|-------|
| **Chart Type** | Bar Chart (Horizontal) |
| **Dimension** | `network` |
| **Metrics** | `total_max_revenue`, `total_network_revenue` |
| **Sort** | `total_max_revenue` DESC |

**Kullanım:** Her network'ün MAX vs kendi raporladığı geliri yan yana gösterir.

#### B) Delta Dağılımı (Bar Chart with Colors)

| Ayar | Değer |
|------|-------|
| **Chart Type** | Bar Chart |
| **Dimension** | `network` |
| **Metric** | `overall_rev_delta_pct` |
| **Conditional Formatting** | Pozitif: Mavi, Negatif: Kırmızı |
| **Reference Line** | 0 ve ±5% çizgileri |

**Kullanım:** Hangi network'ün ne kadar sapma gösterdiğini gösterir.

#### C) Network Durum Tablosu

| Ayar | Değer |
|------|-------|
| **Chart Type** | Table |
| **Columns** | `network`, `last_report_date`, `record_count`, `total_max_revenue`, `overall_rev_delta_pct` |
| **Conditional Formatting** | Delta >5%: Kırmızı background |
| **Sort** | `total_max_revenue` DESC |

**Kullanım:** Tüm network'lerin durumunu tek tabloda gösterir.

#### D) Gelir Payı (Pie/Donut Chart)

| Ayar | Değer |
|------|-------|
| **Chart Type** | Pie Chart veya Donut |
| **Dimension** | `network` |
| **Metric** | `total_max_revenue` |
| **Show Labels** | Percentage |

**Kullanım:** Her network'ün toplam gelirdeki payını gösterir.

#### E) Sync Freshness Indicator

| Ayar | Değer |
|------|-------|
| **Chart Type** | Table with Conditional Formatting |
| **Columns** | `network`, `last_report_date_str`, `last_sync_str` |
| **Calculated Field** | `DATE_DIFF(CURRENT_DATE(), last_report_date, DAY)` |
| **Conditional** | 0-2 gün: Yeşil, 3-5 gün: Sarı, >5 gün: Kırmızı |

### 3. Dashboard Layout Önerisi

```
┌─────────────────────────────────────────────────────────────┐
│            NETWORK PERFORMANCE OVERVIEW                      │
├─────────────────────────────┬───────────────────────────────┤
│                             │                               │
│   [Bar Chart]               │   [Pie Chart]                 │
│   MAX vs Network Revenue    │   Revenue Share by Network    │
│   by Network                │                               │
│                             │                               │
├─────────────────────────────┴───────────────────────────────┤
│                                                             │
│   [Delta Bar Chart]                                         │
│   Revenue Delta % by Network                                │
│   ────────────────────────────────────────                  │
│   Unity     ████████░░░░░░░░░░░░  +3.2%                    │
│   Meta      ██████████████░░░░░░  +7.1%  ⚠️               │
│   IronSource████░░░░░░░░░░░░░░░░  -2.1%                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Status Table]                                            │
│   Network | Last Report | Records | Revenue | Delta         │
│   ─────────────────────────────────────────────────────     │
│   Unity   | 2026-01-04  | 12,345  | $45,678 | +3.2%        │
│   Meta    | 2026-01-04  | 8,901   | $34,567 | +7.1% ⚠️     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4. Calculated Fields

```sql
-- Days Behind
DATE_DIFF(CURRENT_DATE(), last_report_date, DAY)

-- Status Icon
CASE 
    WHEN ABS(overall_rev_delta_pct) > 10 THEN "🔴"
    WHEN ABS(overall_rev_delta_pct) > 5 THEN "🟡"
    ELSE "🟢"
END

-- Revenue Difference (USD)
total_network_revenue - total_max_revenue

-- Revenue Difference (Formatted)
CONCAT(
    CASE WHEN total_network_revenue > total_max_revenue THEN "+" ELSE "" END,
    FORMAT_NUMBER(total_network_revenue - total_max_revenue, 2),
    " USD"
)
```

### 5. Filtreler

| Filtre | Kullanım |
|--------|----------|
| **Network** | Belirli network'lere odaklanma |
| **Delta Threshold** | Sadece >X% sapma gösterenleri göster |
| **Min Revenue** | Küçük network'leri filtrele |

---

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Aggregate Veriler:** Bu view tüm zamanların toplamını gösterir. Tarih bazlı analiz için `network_comparison` kullanın.

2. **Delta Yorumlama:**
   - Pozitif: Network, MAX'tan daha fazla raporluyor
   - Negatif: MAX, network'ten daha fazla raporluyor
   - ±5% arası genellikle kabul edilebilir

3. **Sıralama:** Genellikle `total_max_revenue` DESC sıralaması en anlamlısıdır (büyük network'ler önce).
