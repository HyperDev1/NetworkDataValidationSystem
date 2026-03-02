# Phase 3: Scheduling - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Cloud Scheduler'ın günde 8 kez (her 3 saatte bir, UTC) Cloud Run'daki `/validate` endpoint'ini tetiklemesi ve Cloud Run'ın validation pipeline'ını çalıştırıp HTTP response dönmesi. Yeni bir pipeline özelliği eklemek bu phase'in dışındadır.

</domain>

<decisions>
## Implementation Decisions

### Çalışma zamanı
- Her 3 saatte bir çalışacak: cron `0 */3 * * *` (günde 8 kez: 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00 UTC)
- Timezone: UTC

### Hata response kodu
- `/validate` en az 1 network başarısız olursa **500** döner (kısmi hata dahil)
- Sadece tüm networkler başarılı olursa 200 döner
- Cloud Scheduler 5xx cevabı retry trigger olarak değerlendirir

### Kimlik doğrulama
- Cloud Run endpoint **OIDC** ile korunur (public değil)
- Cloud Scheduler, OIDC token ekleyerek istek atar
- Dedicated service account kullanılır (araştırma/planlama aşamasında belirlenir)

### Retry politikası
- **5 retry**, exponential backoff (Cloud Scheduler default)
- Bekleme: ~1dk → 2dk → 4dk → 8dk → 16dk
- 5 retry sonrası başarısız olursa Cloud Scheduler job'ı failed olarak işaretler

### Claude's Discretion
- Service account adı ve IAM rolleri (mevcut GCP setup'a göre belirlenecek)
- Cloud Scheduler job adı ve açıklaması
- Retry deadline (maximum retry window)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server.py`: Flask HTTP server zaten mevcut — `/health` (GET) ve `/validate` (POST) endpoint'leri yazılmış. Phase 3, bu dosyayı **günceller** (hata response kodu değişikliği).
- `Dockerfile`: `CMD ["python", "server.py"]`, PORT 8080 expose, non-root user — Cloud Run için hazır.
- `scripts/setup-secrets.sh`: Mevcut pattern — Phase 3 için benzer bir Cloud Scheduler setup script'i yazılabilir.

### Established Patterns
- Mevcut `/validate` endpoint başarısız networkler olsa dahi **200** dönüyor. Bu phase 500 davranışına değiştirilecek.
- `result.get('failed_networks', [])` zaten response'a dahil — hata tespiti için kullanılabilir.
- GCP auth pattern: OIDC service account `setup-secrets.sh`'teki `gcloud` komutlarıyla tutarlı kurulacak.

### Integration Points
- `server.py` → `failed_networks` listesi boş değilse 500 dönecek şekilde güncellenir
- Cloud Scheduler → Cloud Run `/validate` POST isteği (OIDC token ile)
- Yeni `scripts/setup-scheduler.sh` → `setup-secrets.sh` ile aynı stil/pattern

</code_context>

<specifics>
## Specific Ideas

- `setup-scheduler.sh` scripti, `setup-secrets.sh` ile aynı stilde olacak — operatör çalıştırır, Cloud Scheduler job'ı oluşturulur
- Script içinde OIDC service account oluşturma, IAM binding, ve `gcloud scheduler jobs create http` komutu yer almalı

</specifics>

<deferred>
## Deferred Ideas

None — tartışma phase scope içinde kaldı.

</deferred>

---

*Phase: 03-scheduling*
*Context gathered: 2026-03-02*
