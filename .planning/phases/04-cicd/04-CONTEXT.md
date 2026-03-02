# Phase 4: CI/CD - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

GitHub Actions'ın her `main` branch push'unda Docker image build etmesi, Google Artifact Registry'ye push etmesi ve Cloud Run service'ini otomatik güncellemesi. Monitoring, alerting ve multi-environment desteği bu phase dışındadır.

</domain>

<decisions>
## Implementation Decisions

### GCP Kimlik Doğrulama (GitHub Actions → GCP)
- **Workload Identity Federation** (keyless) kullanılır — JSON key saklanmaz
- GitHub Actions, kısa ömürlü OIDC token ile GCP'ye authenticate olur
- Gerekli GCP kaynaklar: Workload Identity Pool, Provider, SA binding
- GitHub secret olarak `WIF_PROVIDER` ve `WIF_SERVICE_ACCOUNT` saklanır
- `google-github-actions/auth` action kullanılır (v2)

### Image Tagging
- Her build: commit SHA tag (`sha-{short_sha}`) + `latest` tag
- SHA tag rollback ve traceability sağlar
- `latest` her zaman en yeni production image'ı gösterir
- Image path: `us-central1-docker.pkg.dev/{PROJECT_ID}/network-data-validation/app`

### PR Davranışı
- **PR'larda**: sadece `docker build` — push ve deploy yapılmaz
- **main push'ta**: build + push to Artifact Registry + Cloud Run deploy
- PR build, image'ın kırık olmadığını doğrular ama production'ı etkilemez

### Registry Konumu
- Region: `us-central1` — Cloud Run ile aynı region (latency ve fatura optimumu)
- Artifact Registry repository adı: `network-data-validation`
- Repository formatı: `DOCKER`

### Cloud Run Deploy
- Service adı: `network-data-validation` (setup-scheduler.sh ile tutarlı)
- Region: `us-central1`
- Deploy komutu: `gcloud run deploy` — yeni image SHA ile güncelleme
- `--no-allow-unauthenticated` bayrağı korunur (OIDC zorunlu)

### Workflow Yapısı
- Tek workflow dosyası: `.github/workflows/deploy.yml`
- İki job: `build-and-push` + `deploy` (deploy, push başarılı olursa tetiklenir)
- Workflow sadece `main` branch'inde tetiklenir (`on: push: branches: [main]`)
- PR'larda ayrı `build-check` job'ı çalışır

### Setup Scripti
- `scripts/setup-cicd.sh`: Artifact Registry oluşturma, Workload Identity Pool/Provider kurulumu, SA ve IAM binding — `setup-secrets.sh` stiliyle
- Operatör tek seferlik çalıştırır, sonraki push'larda her şey otomatik

### Claude's Discretion
- Workflow job timeout değerleri
- Docker build cache stratejisi (GitHub Actions cache veya Artifact Registry cache)
- Artifact retention policy (eski image'ları ne kadar saklasın)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile`: Multi-stage build hazır — `docker build .` ile doğrudan kullanılır, değişiklik gerekmez
- `scripts/setup-secrets.sh` ve `scripts/setup-scheduler.sh`: `gcloud` komut stili ve idempotent pattern için referans
- `docker-compose.yml`: Local test ortamı — CI/CD'den bağımsız, dokunulmaz

### Established Patterns
- `scripts/setup-*.sh` pattern: Operatör çalıştırır, ortam değişkeni ile `PROJECT_ID` alır, idempotent
- Cloud Run service adı ve region: `network-data-validation`, `us-central1` — setup-scheduler.sh'tan tutarlı
- `.dockerignore`: Hassas dosyalar zaten hariç tutulmuş — image temiz

### Integration Points
- `main` branch push → GitHub Actions tetikleme
- Artifact Registry ← Docker image push
- Cloud Run ← `gcloud run deploy` ile yeni image
- Workload Identity ← GitHub OIDC token (keyless auth)
- GitHub repository secrets: `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`

</code_context>

<specifics>
## Specific Ideas

- Kullanıcı notu: "sistemi localde çalışır hale getirdikten sonra google cloud'a aktarmamız gerekiyor" — bu phase, local'de çalışan sistemi (Phase 1-3) tam otomatik cloud deployment'a taşıyan son adımdır
- `setup-cicd.sh` scripti, Workload Identity kurulumunu adım adım açıklayan yorumlarla belgelenmiş olmalı (karmaşık GCP kurulumu)
- PR'da build-check job'ı hızlı geri bildirim verir (merge öncesi Dockerfile kırık mı?)

</specifics>

<deferred>
## Deferred Ideas

- Staging environment — birden fazla ortam bu milestone dışında
- Rollback komutu / workflow — manuel rollback gelecekte eklenebilir
- Cloud Monitoring / alerting — REQUIREMENTS.md'de Future Requirements olarak işaretli
- Semantic versioning / release tags — şimdilik commit SHA yeterli

</deferred>

---

*Phase: 04-cicd*
*Context gathered: 2026-03-02*
