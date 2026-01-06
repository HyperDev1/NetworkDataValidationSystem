# BigQuery Tables Documentation

Bu klasör, Network Data Validation System'in BigQuery tablolarının detaylı dokümantasyonunu içerir.

## 📊 Tablolar

| Dosya | Tablo | Açıklama |
|-------|-------|----------|
| [network_comparison.md](network_comparison.md) | `network_comparison` | Ana veri tablosu - tüm karşılaştırma verileri |
| [sync_metadata.md](sync_metadata.md) | `sync_metadata` | Genel sistem durumu (tek satır) |
| [network_sync_summary.md](network_sync_summary.md) | `network_sync_summary` | Network bazlı özet |
| [network_data_availability.md](network_data_availability.md) | `network_data_availability` | Veri güncelliği takibi |

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                         GCS                                  │
│   gs://applovin_max_network_data/network_data/dt=YYYY-MM-DD │
│                    (Parquet files)                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   network_comparison                         │
│                   (External Table)                           │
│   - Ana veri kaynağı                                        │
│   - GCS'den direkt okur                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐
    │ sync_metadata │ │network_sync_  │ │network_data_      │
    │    (View)     │ │   summary     │ │   availability    │
    │               │ │    (View)     │ │      (View)       │
    │ Genel durum   │ │ Network özet  │ │ Güncellik takibi  │
    │ (1 satır)     │ │ (N satır)     │ │ (N satır)         │
    └───────────────┘ └───────────────┘ └───────────────────┘
```

## 🎯 Looker Dashboard Yapısı Önerisi

```
┌─────────────────────────────────────────────────────────────┐
│   HEADER (sync_metadata)                                     │
│   [Son Sync] [Network Sayısı] [Toplam Kayıt] [Sync Status]  │
├─────────────────────────────────────────────────────────────┤
│   PAGE 1: Overview                                           │
│   - Network Gelir Karşılaştırma (network_sync_summary)      │
│   - Delta Dağılımı (network_sync_summary)                   │
│   - Veri Güncelliği (network_data_availability)             │
├─────────────────────────────────────────────────────────────┤
│   PAGE 2: Detailed Analysis                                  │
│   - Günlük Trend (network_comparison)                       │
│   - Platform Breakdown (network_comparison)                 │
│   - Ad Type Breakdown (network_comparison)                  │
├─────────────────────────────────────────────────────────────┤
│   PAGE 3: Alerts                                             │
│   - Tutarsızlık Listesi (network_comparison, delta>5%)      │
│   - Geciken Network'ler (network_data_availability)         │
└─────────────────────────────────────────────────────────────┘
```

## 📁 İlgili Dosyalar

- [setup_bigquery.sql](../../scripts/setup_bigquery.sql) - Tablo/view tanımlamaları
- [update_views.py](../../scripts/update_views.py) - View güncelleme scripti
- [gcs_exporter.py](../../src/exporters/gcs_exporter.py) - GCS'e veri yazma
