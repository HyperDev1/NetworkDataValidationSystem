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
| `total_networks` | INT64 | Toplam aktif network sayısı |
| `total_records` | INT64 | Toplam kayıt sayısı |
| `last_report_date` | DATE | En son rapor tarihi |
| `first_report_date` | DATE | En eski rapor tarihi |
| `last_sync_time` | TIMESTAMP | Son senkronizasyon zamanı |
| `last_report_date_str` | STRING | Formatlanmış son rapor tarihi |
| `first_report_date_str` | STRING | Formatlanmış ilk rapor tarihi |
| `last_sync_str` | STRING | Formatlanmış son sync zamanı |
| `last_sync_display` | STRING | Okunabilir format (ör: "2 saat önce") |
| `status_line` | STRING | Durum özeti satırı |
| `hours_since_last_sync` | INT64 | Son sync'den bu yana geçen saat |
| `total_max_revenue` | FLOAT64 | Toplam MAX geliri |
| `total_network_revenue` | FLOAT64 | Toplam network geliri |

## 🔍 Örnek Sorgular

### Basit durum kontrolü
```sql
SELECT * FROM `gen-lang-client-0468554395.ad_network_analytics.sync_metadata`
```

### Sync sağlığı kontrolü
```sql
SELECT 
    CASE 
        WHEN hours_since_last_sync < 6 THEN '🟢 Healthy'
        WHEN hours_since_last_sync < 24 THEN '🟡 Warning'
        ELSE '🔴 Critical'
    END as sync_status,
    last_sync_display,
    total_networks,
    total_records
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

#### B) Toplam Network Sayısı Scorecard

| Ayar | Değer |
|------|-------|
| **Chart Type** | Scorecard |
| **Metric** | `total_networks` |
| **Label** | "Aktif Network" |

#### C) Toplam Kayıt Scorecard

| Ayar | Değer |
|------|-------|
| **Chart Type** | Scorecard |
| **Metric** | `total_records` |
| **Label** | "Toplam Kayıt" |
| **Format** | Number (thousands separator) |

#### D) Veri Aralığı Scorecard

| Ayar | Değer |
|------|-------|
| **Chart Type** | Scorecard |
| **Metric** | `status_line` |
| **Label** | "Veri Aralığı" |

#### E) Sync Sağlığı Göstergesi

| Ayar | Değer |
|------|-------|
| **Chart Type** | Scorecard with Conditional Formatting |
| **Metric** | `hours_since_last_sync` |
| **Conditional** | <6: Yeşil, <24: Sarı, >24: Kırmızı |

### 3. Dashboard Layout Önerisi

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER ROW (sync_metadata view'dan)                        │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Son Sync │ Network  │ Toplam   │  Veri    │  Sync           │
│ Zamanı   │ Sayısı   │ Kayıt    │  Aralığı │  Durumu         │
│ ──────── │ ──────── │ ──────── │ ──────── │ ─────────────── │
│ 2 sa önce│    12    │  45,678  │ 90 gün   │     🟢          │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

### 4. Calculated Fields

```sql
-- Sync Status Emoji
CASE 
    WHEN hours_since_last_sync < 6 THEN "🟢"
    WHEN hours_since_last_sync < 24 THEN "🟡"
    ELSE "🔴"
END

-- Revenue Summary
CONCAT(
    "MAX: $", FORMAT_NUMBER(total_max_revenue, 0),
    " | Network: $", FORMAT_NUMBER(total_network_revenue, 0)
)
```

---

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Tek Satır:** Bu view her zaman tek satır döner. Tablo veya chart yerine Scorecard kullanın.

2. **Real-time:** View olduğu için her sorguda güncel veri alırsınız, cache sorunu olmaz.

3. **Sync Sağlığı Eşikleri:**
   - < 6 saat: Normal (günlük sync)
   - 6-24 saat: Kontrol edilmeli
   - > 24 saat: Sync problemi olabilir
