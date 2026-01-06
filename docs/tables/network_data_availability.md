# network_data_availability

Her network için veri güncelliği ve gecikme durumunu takip eden view. Her network'ün API gecikme süresini (expected_delay_days) dikkate alarak gerçek durumu hesaplar.

## 📋 Genel Bilgi

| Özellik | Değer |
|---------|-------|
| **Tür** | View |
| **Kaynak** | `network_comparison` tablosundan türetilir |
| **Satır Sayısı** | Network sayısı kadar (örn: 12) |
| **Güncelleme** | Real-time (view olduğu için) |
| **Özel Özellik** | Network bazlı beklenen gecikme süreleri tanımlı |

## 📊 Şema

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `network` | STRING | Network adı |
| `record_count` | INT64 | Bu network için toplam kayıt sayısı |
| `last_report_date` | DATE | Bu network için en son rapor tarihi |
| `last_sync_time` | TIMESTAMP | Bu network için son sync zamanı |
| `last_report_date_str` | STRING | Formatlanmış son rapor tarihi |
| `last_sync_str` | STRING | Formatlanmış son sync zamanı |
| `expected_delay_days` | INT64 | Bu network'ün beklenen API gecikmesi (gün) |
| `expected_latest_date` | DATE | Bu network için beklenen en güncel tarih |
| `days_behind_expected` | INT64 | Beklentiden kaç gün geride |
| `status` | STRING | "OK" veya "X days behind" |
| `total_max_revenue` | FLOAT64 | Bu network'ün toplam MAX geliri |
| `total_network_revenue` | FLOAT64 | Bu network'ün toplam kendi raporladığı gelir |
| `overall_rev_delta_pct` | FLOAT64 | Genel gelir farkı yüzdesi |

## 🕐 Network Gecikme Süreleri

Her network'ün API'si farklı gecikme süresiyle veri sunar:

| Network | Beklenen Gecikme | Açıklama |
|---------|------------------|----------|
| AdMob | 1 gün | Hızlı API |
| Unity | 1 gün | Hızlı API |
| Meta | 2 gün | Orta gecikme |
| IronSource | 2 gün | Orta gecikme |
| AppLovin | 1 gün | Hızlı API |
| Mintegral | 2 gün | Orta gecikme |
| Pangle | 3 gün | Yavaş API |
| Liftoff | 2 gün | Orta gecikme |
| Moloco | 2 gün | Orta gecikme |
| InMobi | 2 gün | Orta gecikme |
| BidMachine | 1 gün | Hızlı API |
| DT Exchange | 2 gün | Orta gecikme |

## 🔍 Örnek Sorgular

### Tüm network'lerin güncellik durumu
```sql
SELECT 
    network,
    last_report_date,
    expected_delay_days,
    expected_latest_date,
    days_behind_expected,
    status
FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability`
ORDER BY days_behind_expected DESC
```

### Geride kalan network'ler
```sql
SELECT *
FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability`
WHERE days_behind_expected > 0
ORDER BY days_behind_expected DESC
```

### Sağlıklı network'ler
```sql
SELECT network, status, last_report_date
FROM `gen-lang-client-0468554395.ad_network_analytics.network_data_availability`
WHERE status = 'OK'
```

---

## 📈 Looker Kullanımı

### 1. Data Source Oluşturma

1. Looker Studio'da **Add Data** → **BigQuery** seç
2. Project: `gen-lang-client-0468554395`
3. Dataset: `ad_network_analytics`
4. Table: `network_data_availability`

### 2. Önerilen Grafikler

#### A) Network Sağlık Durumu Tablosu (Ana Görünüm)

| Ayar | Değer |
|------|-------|
| **Chart Type** | Table |
| **Columns** | `network`, `status`, `last_report_date_str`, `days_behind_expected`, `expected_delay_days` |
| **Conditional Formatting** | `status` = "OK": Yeşil, diğer: Kırmızı |
| **Sort** | `days_behind_expected` DESC |

**Kullanım:** Hangi network'ün veri çekme problemi olduğunu gösterir.

#### B) Gecikme Günleri Bar Chart

| Ayar | Değer |
|------|-------|
| **Chart Type** | Bar Chart (Horizontal) |
| **Dimension** | `network` |
| **Metric** | `days_behind_expected` |
| **Conditional Formatting** | 0: Yeşil, 1-2: Sarı, >2: Kırmızı |
| **Reference Line** | 0 (hedef) |

**Kullanım:** Hangi network'ün ne kadar geride olduğunu görselleştirir.

#### C) Status Özet Scorecards

| Widget | Metric | Açıklama |
|--------|--------|----------|
| **Scorecard 1** | `COUNTIF(status = 'OK')` | Sağlıklı network sayısı |
| **Scorecard 2** | `COUNTIF(status != 'OK')` | Problemli network sayısı |
| **Scorecard 3** | `MAX(days_behind_expected)` | En kötü gecikme |

#### D) Timeline/Gantt Görünümü

| Ayar | Değer |
|------|-------|
| **Chart Type** | Timeline veya Custom |
| **Rows** | `network` |
| **Start** | `last_report_date` |
| **End** | `CURRENT_DATE()` |
| **Color** | `status` bazlı |

**Kullanım:** Her network'ün veri boşluğunu görsel olarak gösterir.

#### E) Alert List (Problemli Network'ler)

| Ayar | Değer |
|------|-------|
| **Chart Type** | Table |
| **Filter** | `days_behind_expected > 0` |
| **Columns** | `network`, `status`, `last_report_date`, `days_behind_expected` |
| **Highlight** | Tüm satırlar kırmızı/turuncu background |

### 3. Dashboard Layout Önerisi

```
┌─────────────────────────────────────────────────────────────┐
│              DATA AVAILABILITY MONITOR                       │
├──────────────┬──────────────┬───────────────────────────────┤
│   🟢 OK      │   🔴 Behind  │   ⏰ Max Delay                │
│   ────────   │   ────────   │   ──────────                  │
│      10      │      2       │    3 days                     │
│   networks   │   networks   │   (Pangle)                    │
├──────────────┴──────────────┴───────────────────────────────┤
│                                                             │
│   [Status Table]                                            │
│   Network    | Status | Last Data | Expected | Behind       │
│   ──────────────────────────────────────────────────────    │
│   Unity      | 🟢 OK  | Jan 05    | Jan 05   | 0 days      │
│   Meta       | 🟢 OK  | Jan 04    | Jan 04   | 0 days      │
│   Pangle     | 🔴     | Jan 01    | Jan 03   | 2 days ⚠️   │
│   IronSource | 🟢 OK  | Jan 04    | Jan 04   | 0 days      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Delay Bar Chart]                                         │
│                                                             │
│   Unity      ░░░░░░░░░░░░░░░░░░░░  0 days                  │
│   Meta       ░░░░░░░░░░░░░░░░░░░░  0 days                  │
│   Pangle     ████████░░░░░░░░░░░░  2 days ⚠️               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4. Calculated Fields

```sql
-- Status Emoji
CASE 
    WHEN status = 'OK' THEN "🟢"
    WHEN days_behind_expected <= 2 THEN "🟡"
    ELSE "🔴"
END

-- Days Behind (Formatted)
CASE 
    WHEN days_behind_expected = 0 THEN "On track"
    WHEN days_behind_expected = 1 THEN "1 day behind"
    ELSE CONCAT(days_behind_expected, " days behind")
END

-- Health Score (0-100)
CASE 
    WHEN days_behind_expected = 0 THEN 100
    WHEN days_behind_expected = 1 THEN 75
    WHEN days_behind_expected = 2 THEN 50
    ELSE 25
END

-- Alert Priority
CASE 
    WHEN days_behind_expected > 3 THEN "Critical"
    WHEN days_behind_expected > 1 THEN "Warning"
    ELSE "Normal"
END
```

### 5. Alert Kuralları

Bu view özellikle monitoring/alerting için kullanışlıdır:

| Durum | Aksiyon |
|-------|---------|
| `days_behind_expected = 0` | Normal, aksiyon gerekmez |
| `days_behind_expected = 1-2` | İzle, geçici olabilir |
| `days_behind_expected > 2` | API problemi, kontrol et |
| `days_behind_expected > 5` | Kritik, acil müdahale |

---

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Expected Delay Doğruluğu:** Her network'ün `expected_delay_days` değeri doğru ayarlanmalı. Yeni network eklendiğinde [update_views.py](../../scripts/update_views.py) güncellenmeli.

2. **Hafta Sonu Etkisi:** Bazı network'ler hafta sonları güncelleme yapmayabilir. Pazartesi günleri `days_behind_expected` artabilir.

3. **Status Yorumlama:**
   - "OK": Network beklenen sürede veri sağlıyor
   - "X days behind": Network beklentiden X gün geride

4. **False Positive:** Yeni entegre edilen network'ler başlangıçta "behind" görünebilir, bu normal.
