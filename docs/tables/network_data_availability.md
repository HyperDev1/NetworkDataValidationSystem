# network_data_availability

Her network için sync durumu ve son rapor tarihlerini takip eden view.

## 📋 Genel Bilgi

| Özellik | Değer |
|---------|-------|
| **Tür** | View |
| **Kaynak** | `network_comparison` tablosundan türetilir |
| **Satır Sayısı** | Network sayısı kadar (örn: 12) |
| **Güncelleme** | Real-time (view olduğu için) |
| **Sıralama** | `last_report_date DESC` |

## 📊 Şema

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `network` | STRING | Network adı |
| `record_count` | INT64 | Bu network için toplam kayıt sayısı |
| `last_report_date` | DATE | Bu network için en son rapor tarihi |
| `last_sync_time` | TIMESTAMP | Bu network için son sync zamanı |
| `last_report_date_str` | STRING | Formatlanmış son rapor tarihi (Looker display için) |
| `last_sync_str` | STRING | Formatlanmış son sync zamanı (Looker display için) |

## 🔍 Örnek Sorgular

### Tüm network'lerin sync durumu
```sql
SELECT 
    network,
    record_count,
    last_report_date,
    last_sync_time
FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability`
ORDER BY last_report_date DESC
```

### En çok kayıt olan network'ler
```sql
SELECT network, record_count, last_report_date_str
FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability`
ORDER BY record_count DESC
```

### Belirli bir tarihten eski verisi olan network'ler
```sql
SELECT network, last_report_date
FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability`
WHERE last_report_date < DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
```

---

## 📈 Looker Kullanımı

### 1. Data Source Oluşturma

1. Looker Studio'da **Add Data** → **BigQuery** seç
2. Project: `gen-lang-client-0468554395`
3. Dataset: `ad_network_analytics`
4. Table: `network_data_availability`

### 2. Önerilen Grafikler

#### A) Network Sync Durumu Tablosu

| Ayar | Değer |
|------|-------|
| **Chart Type** | Table |
| **Columns** | `network`, `record_count`, `last_report_date_str`, `last_sync_str` |
| **Sort** | `last_report_date` DESC |

**Kullanım:** Her network'ün son veri tarihini ve toplam kayıt sayısını gösterir.

#### B) Kayıt Sayısı Bar Chart

| Ayar | Değer |
|------|-------|
| **Chart Type** | Bar Chart (Horizontal) |
| **Dimension** | `network` |
| **Metric** | `record_count` |
| **Sort** | `record_count` DESC |

**Kullanım:** Network'ler arası veri hacmi karşılaştırması.

#### C) Özet Scorecards

| Widget | Metric | Açıklama |
|--------|--------|----------|
| **Scorecard 1** | `COUNT(network)` | Toplam network sayısı |
| **Scorecard 2** | `SUM(record_count)` | Toplam kayıt sayısı |
| **Scorecard 3** | `MAX(last_report_date)` | En güncel rapor tarihi |

### 3. Dashboard Layout Önerisi

```
┌─────────────────────────────────────────────────────────────┐
│              NETWORK SYNC MONITOR                            │
├──────────────┬──────────────┬───────────────────────────────┤
│   📊 Total   │   📝 Records │   📅 Latest Report            │
│   ────────   │   ────────   │   ──────────                  │
│      12      │    125,000   │    2026-01-06                 │
│   networks   │   total rows │                               │
├──────────────┴──────────────┴───────────────────────────────┤
│                                                             │
│   [Sync Status Table]                                       │
│   Network    | Records | Last Report  | Last Sync          │
│   ──────────────────────────────────────────────────────    │
│   Unity      | 15,234  | 2026-01-06   | 2026-01-07 10:30   │
│   Meta       | 12,456  | 2026-01-05   | 2026-01-07 10:30   │
│   IronSource | 11,234  | 2026-01-06   | 2026-01-07 10:30   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Record Count Bar Chart]                                  │
│                                                             │
│   Unity      ████████████████████  15,234                  │
│   Meta       ███████████████░░░░░  12,456                  │
│   IronSource ██████████████░░░░░░  11,234                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Troubleshooting

### STRING Field'lar Looker'da Görünmüyor

Eğer `last_report_date_str` veya `last_sync_str` gibi STRING field'lar Looker Studio'da dimension/metric listesinde görünmüyorsa:

1. **Data Source'u Yenile:**
   - Looker Studio'da data source'a git
   - Sağ üstteki **"Refresh Fields"** butonuna tıkla
   - Bu, BigQuery'den şemayı yeniden çekecektir

2. **Field Tiplerini Kontrol Et:**
   - Data source editor'da field'ların tipini kontrol et
   - STRING field'lar "Text" olarak görünmeli

3. **Cache'i Temizle:**
   - Data source ayarlarından "Data freshness" → "No cache" dene
   - Dashboard'u yeniden yükle

4. **Yeni Data Source Oluştur:**
   - Sorun devam ederse, aynı tablo için yeni bir data source oluştur
