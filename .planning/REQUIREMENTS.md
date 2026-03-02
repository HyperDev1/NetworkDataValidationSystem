# Requirements: Network Data Validation System

**Defined:** 2026-03-02
**Core Value:** Ad network gelir verilerini AppLovin MAX ile otomatik karşılaştırarak discrepancy'leri tespit etmek

## v1.0.1 Requirements

Requirements for Google Cloud Run deployment. Each maps to roadmap phases.

### Containerization

- [x] **CONT-01**: Uygulama multi-stage Dockerfile ile production-ready container image olarak build edilebilir
- [x] **CONT-02**: .dockerignore ile gereksiz dosyalar (credentials/, config.yaml, .git) image dışında kalır
- [x] **CONT-03**: Cloud Run container health check'e HTTP endpoint üzerinden yanıt verir
- [x] **CONT-04**: Container lokal ortamda docker build + docker run ile test edilebilir

### Secret Management

- [x] **SEC-01**: config.yaml'daki tüm API key/token/credential'lar GCP Secret Manager'a taşınır
- [x] **SEC-02**: Cloud Run, secret'ları environment variable olarak container'a inject eder
- [x] **SEC-03**: config.py, önce environment variable'ları kontrol eder, yoksa config.yaml'a fallback yapar
- [x] **SEC-04**: AdMob OAuth refresh token Secret Manager'da saklanır ve Cloud Run tarafından okunur

### Scheduling

- [ ] **SCHED-01**: Cloud Scheduler günlük tek bir saatte Cloud Run service'i tetikler
- [ ] **SCHED-02**: Cloud Run HTTP trigger ile validation çalıştırıp sonucu döner

### CI/CD

- [ ] **CICD-01**: GitHub Actions workflow, main branch'e push'ta Docker image build eder
- [ ] **CICD-02**: Build edilen image Google Artifact Registry'ye push edilir
- [ ] **CICD-03**: Push sonrası Cloud Run service otomatik olarak yeni image ile deploy edilir

## Future Requirements

### Monitoring & Observability

- **MON-01**: Cloud Monitoring dashboard ile validation run metrikleri izlenebilir
- **MON-02**: Başarısız validation run'lar için alert policy (email/Slack)

### Infrastructure as Code

- **IAC-01**: Tüm GCP kaynakları Terraform ile yönetilebilir
- **IAC-02**: Multi-environment (staging/production) desteği

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud Monitoring dashboard/alerting | Cloud Logging yeterli, ekstra karmaşıklık gereksiz |
| Terraform/IaC | Manuel GCP setup şimdilik yeterli |
| Kubernetes deployment | Cloud Run serverless yeterli |
| Multi-region deployment | Tek region yeterli, performans kritik değil |
| Database entegrasyonu | Stateless model korunacak |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONT-01 | Phase 1 | Complete (01-01) |
| CONT-02 | Phase 1 | Complete (01-01) |
| CONT-03 | Phase 1 | Complete (01-01) |
| CONT-04 | Phase 1 | Complete (01-02) |
| SEC-01 | Phase 2 | Complete (02-01, 02-02) |
| SEC-02 | Phase 2 | Complete (02-01, 02-02) |
| SEC-03 | Phase 2 | Complete (02-01) |
| SEC-04 | Phase 2 | Complete (02-02, 02-03) |
| SCHED-01 | Phase 3 | Pending |
| SCHED-02 | Phase 3 | Pending |
| CICD-01 | Phase 4 | Pending |
| CICD-02 | Phase 4 | Pending |
| CICD-03 | Phase 4 | Pending |

**Coverage:**
- v1.0.1 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after roadmap creation — all requirements mapped*
