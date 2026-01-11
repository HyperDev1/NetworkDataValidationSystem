# sync_metadata

Tüm sistemin genel senkronizasyon durumunu gösteren özet view. Dashboard header'ı için idealdir.

## 📋 Genel Bilgi

| Özellik | Değer |
|---------|-------|
| **Tür** | View |
| **Kaynak** | `network_comparison` tablosundan türetilir |
| **Satır Sayısı** | Her zaman 1 satır |
| **Güncelleme** | Real-time (view olduğu için) |

## 📊 Şema

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `last_sync_time` | TIMESTAMP | Son senkronizasyon zamanı |
| `last_sync_str` | STRING | Formatlanmış son sync zamanı |
| `last_sync_display` | STRING | Okunabilir format (ör: "2 saat önce") |

## 🔍 Örnek Sorgular

### Basit durum kontrolü
```sql
SELECT * FROM `gen-lang-client-0468554395.ad_network_analytics.sync_metadata`
```

### Sync sağlığı kontrolü
```sql
SELECT 
    last_sync_display,
    last_sync_str
FROM `gen-lang-client-0468554395.ad_network_analytics.sync_metadata`
```

---

## 📈 Looker Kullanımı

### 1. Data Source Oluşturma

1. Looker Studio'da **Add Data** → **BigQuery** seç
2. Project: `gen-lang-client-0468554395`
3. Dataset: `ad_network_analytics`
4. Table: `sync_metadata`

### 2. Önerilen Kullanım: Dashboard Header

Bu view tek satır döndürür, bu yüzden **Scorecard** widget'ları için idealdir.

#### A) Son Sync Zamanı Scorecard

| Ayar | Değer |
|------|-------|
| **Chart Type** | Scorecard |
| **Metric** | `last_sync_str` veya `last_sync_display` |
| **Label** | "Son Güncelleme" |

### 3. Dashboard Layout Önerisi

```
┌─────────────────────────────────────────┐
│  HEADER ROW (sync_metadata view'dan)    │
├───────────────────┬─────────────────────┤
│    Son Sync       │   Son Rapor         │
│    Zamanı         │   Tarihi            │
│ ───────────────── │ ─────────────────── │
│    2 sa önce      │   2026-01-05        │
└───────────────────┴─────────────────────┘
```

---

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Tek Satır:** Bu view her zaman tek satır döner. Tablo veya chart yerine Scorecard kullanın.

2. **Real-time:** View olduğu için her sorguda güncel veri alırsınız, cache sorunu olmaz.
