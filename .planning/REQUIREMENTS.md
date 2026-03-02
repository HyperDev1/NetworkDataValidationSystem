# Requirements: Network Data Validation System

**Defined:** 2026-03-02
**Core Value:** Ad network gelir verilerini AppLovin MAX ile otomatik karşılaştırarak discrepancy'leri tespit etmek

## v1.0.1 Requirements

Requirements for Google Cloud Run deployment. Each maps to roadmap phases.

### Containerization

- [ ] **CONT-01**: Uygulama multi-stage Dockerfile ile production-ready container image olarak build edilebilir
- [ ] **CONT-02**: .dockerignore ile gereksiz dosyalar (credentials/, config.yaml, .git) image dışında kalır
- [ ] **CONT-03**: Cloud Run container health check'e HTTP endpoint üzerinden yanıt verir
- [ ] **CONT-04**: Container lokal ortamda docker build + docker run ile test edilebilir

### Secret Management

- [ ] **SEC-01**: config.yaml'daki tüm API key/token/credential'lar GCP Secret Manager'a taşınır
- [ ] **SEC-02**: Cloud Run, secret'ları environment variable olarak container'a inject eder
- [ ] **SEC-03**: config.py, önce environment variable'ları kontrol eder, yoksa config.yaml'a fallback yapar
- [ ] **SEC-04**: AdMob OAuth refresh token Secret Manager'da saklanır ve Cloud Run tarafından okunur

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
| CONT-01 | — | Pending |
| CONT-02 | — | Pending |
| CONT-03 | — | Pending |
| CONT-04 | — | Pending |
| SEC-01 | — | Pending |
| SEC-02 | — | Pending |
| SEC-03 | — | Pending |
| SEC-04 | — | Pending |
| SCHED-01 | — | Pending |
| SCHED-02 | — | Pending |
| CICD-01 | — | Pending |
| CICD-02 | — | Pending |
| CICD-03 | — | Pending |

**Coverage:**
- v1.0.1 requirements: 13 total
- Mapped to phases: 0
- Unmapped: 13

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after initial definition*
