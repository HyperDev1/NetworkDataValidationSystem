# Network Data Validation System

## What This Is

Ad network gelirlerini doğrulayan bir Python pipeline'ı. AppLovin MAX'ten (mediation) baseline veri çeker, 12 ad network API'sinden (Meta, Unity, Mintegral, IronSource, Liftoff, DT Exchange, Pangle, BidMachine, InMobi, Moloco, AdMob) paralel olarak gerçek verileri toplar, revenue/impressions/eCPM deltalarını hesaplar, eşik aşımlarını Slack'e bildirir ve tüm karşılaştırma verilerini GCS'ye Parquet formatında export eder.

## Core Value

Ad network gelir verilerini AppLovin MAX mediation verileriyle otomatik karşılaştırarak discrepancy'leri tespit etmek ve raporlamak.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- Async paralel veri çekme (12 ad network + AppLovin MAX baseline)
- Revenue/impressions/eCPM delta hesaplama ve karşılaştırma
- Slack bildirimleri (eşik bazlı filtreleme, network emoji ikonları)
- GCS Parquet export (Hive partitioning, BigQuery uyumlu)
- Scheduled mode (configurable times, 30s interval loop)
- Service mode (PID tracking, start/stop/restart)
- Graceful degradation (başarısız network'ler raporda gösterilir)
- Token caching (OAuth token'lar dosya bazlı TTL cache)

### Active

<!-- Current scope. Building toward these. -->

- [ ] Cloud Run containerization (Dockerfile, production-ready image)
- [ ] GCP Secret Manager entegrasyonu (config.yaml secret'larını taşıma)
- [ ] Cloud Scheduler ile otomatik tetikleme
- [ ] GitHub Actions CI/CD pipeline (build, push, deploy)
- [ ] AdMob OAuth token yönetimi (Secret Manager üzerinden)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Cloud Monitoring dashboard/alerting — Cloud Logging yeterli, ekstra karmaşıklık gereksiz
- Kubernetes deployment — Cloud Run serverless yeterli
- Terraform/IaC — Manuel GCP setup şimdilik yeterli
- Database entegrasyonu — Stateless model korunacak

## Context

- Mevcut codebase Python 3.13.5, aiohttp/asyncio tabanlı
- Config dosyası YAML formatında, tüm secret'lar burada
- AdMob browser-based OAuth 2.0 gerektiriyor — Cloud Run'da lokalde alınmış token Secret Manager'dan okunacak
- GCS export zaten çalışıyor, Cloud Run service account üzerinden devam edecek
- CI/CD pipeline yok, GitHub Actions ile eklenecek

## Constraints

- **Runtime**: Python 3.13.5 — mevcut codebase ile uyumluluk
- **Platform**: Google Cloud Run — serverless, container-based
- **Auth**: GCP service account — Cloud Run'da ADC kullanımı
- **Secrets**: GCP Secret Manager — config.yaml'daki hassas veriler taşınacak
- **Scheduling**: Cloud Scheduler — mevcut schedule kütüphanesi yerine

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Cloud Run (Service değil Job) | Scheduler tetiklemeli, kısa süreli çalışma | — Pending |
| Secret Manager | config.yaml'daki secret'lar güvenli değil, rotation desteği | — Pending |
| GitHub Actions CI/CD | Repo zaten GitHub'da, native entegrasyon | — Pending |
| Cloud Logging (ekstra monitoring yok) | Mevcut Python logging yeterli, Cloud Run otomatik yakalar | — Pending |

---
*Last updated: 2026-03-02 after initial project setup*
