# Network Data Validation System - Agent Guide

Bu döküman, AI agent'ların bu projeyi anlaması ve yeni bileşenler eklemesi için hazırlanmıştır.

## 🎯 Proje Amacı

Bu sistem, reklam ağlarının gelir verilerini karşılaştırır:
- **AppLovin MAX** (mediation platformu - baseline data)
- **Bireysel network'ler** (AdMob, Meta, Unity, Mintegral, Moloco vb.)

Amaç: MAX'ın raporladığı gelir ile network'lerin kendi raporladığı gelir arasındaki tutarsızlıkları tespit etmek.

## 📁 Proje Yapısı

```
NetworkDataValidationSystem/
├── main.py                    # Ana giriş noktası
├── config.yaml                # Aktif konfigürasyon (gitignore'da)
├── config.yaml.example        # Örnek konfigürasyon
├── requirements.txt           # Python bağımlılıkları
├── credentials/               # OAuth token'ları (gitignore'da)
├── templates/                 # Yeni bileşen şablonları
│   ├── network_fetcher_template.py
│   ├── test_network_template.py
│   └── api_analysis_checklist.md
├── src/
│   ├── config.py              # Konfigürasyon yöneticisi
│   ├── validation_service.py  # Ana orkestrasyon servisi
│   ├── fetchers/              # Network veri çekicileri
│   │   ├── base_fetcher.py    # Abstract base class
│   │   ├── applovin_fetcher.py
│   │   ├── admob_fetcher.py
│   │   ├── meta_fetcher.py
│   │   ├── moloco_fetcher.py
│   │   ├── mintegral_fetcher.py
│   │   ├── unity_fetcher.py
│   │   └── __init__.py        # Export'lar
│   ├── validators/            # Veri karşılaştırıcıları
│   │   ├── data_validator.py
│   │   └── __init__.py
│   └── notifiers/             # Bildirim servisleri
│       ├── slack_notifier.py
│       └── __init__.py
└── test_*.py                  # Network test scriptleri
```

## 🔄 Veri Akışı

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py                                   │
│                           │                                      │
│                           ▼                                      │
│                  ValidationService                               │
│                    │         │                                   │
│          ┌────────┴─────────┴────────┐                          │
│          ▼                           ▼                          │
│   ApplovinFetcher              NetworkFetchers                  │
│   (MAX baseline)               (moloco, meta, etc.)             │
│          │                           │                          │
│          └───────────┬───────────────┘                          │
│                      ▼                                          │
│               DataValidator                                     │
│              (compare metrics)                                  │
│                      │                                          │
│                      ▼                                          │
│              SlackNotifier                                      │
│            (send discrepancy alerts)                            │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Standart Veri Yapısı

Tüm fetcher'lar bu yapıyı döndürmelidir:

```python
{
    'revenue': float,           # Toplam gelir (USD)
    'impressions': int,         # Toplam gösterim
    'ecpm': float,              # (revenue / impressions) * 1000
    'network': str,             # Network adı (örn: "Moloco")
    'date_range': {
        'start': 'YYYY-MM-DD',
        'end': 'YYYY-MM-DD'
    },
    'platform_data': {
        'android': {
            'revenue': float,
            'impressions': int,
            'ecpm': float,
            'ad_data': {
                'banner': {'revenue': float, 'impressions': int, 'ecpm': float},
                'interstitial': {'revenue': float, 'impressions': int, 'ecpm': float},
                'rewarded': {'revenue': float, 'impressions': int, 'ecpm': float}
            }
        },
        'ios': {
            # Aynı yapı
        }
    }
}
```

## ⚙️ Konfigürasyon Yapısı

### config.yaml Şeması

```yaml
# AppLovin MAX (baseline)
applovin:
  api_key: "YOUR_API_KEY"
  applications:
    - app_name: "App Name"
      display_name: "Display Name"
      platform: "Android"  # veya "iOS"

# Network'ler
networks:
  network_name:
    enabled: true/false
    # Authentication (network'e göre değişir)
    api_key: "..."        # API Key auth
    access_token: "..."   # Bearer token auth
    email: "..."          # Email/password auth
    password: "..."
    # Filtering (opsiyonel)
    app_ids: "id1,id2"
    # Network-specific
    publisher_id: "..."
    time_zone: "UTC"

# Slack bildirimleri
slack:
  webhook_url: "https://hooks.slack.com/..."
  channel: "#revenue-alerts"

# Raporlama
validation:
  date_range_days: 1
```

## 🔐 Authentication Tipleri

### 1. API Key (Header)
```python
headers = {'Authorization': f'Bearer {api_key}'}
# veya
headers = {'X-API-Key': api_key}
# veya query param
params = {'apikey': api_key}
```

### 2. OAuth 2.0 (Token Refresh)
```python
# Token dosyadan yüklenir ve gerektiğinde refresh edilir
# Örnek: AdMob (Google OAuth)
credentials = Credentials.from_authorized_user_file(token_path)
if credentials.expired:
    credentials.refresh(Request())
```

### 3. Session-based (Login → Token)
```python
# Önce login, sonra token kullan
# Örnek: Moloco
auth_response = requests.post(AUTH_URL, json={'email': email, 'password': password})
token = auth_response.json()['token']
headers = {'Authorization': f'Bearer {token}'}
```

## 🗺️ Platform ve Ad Type Mapping

### Platform Mapping
```python
PLATFORM_MAP = {
    'ANDROID': 'android',
    'IOS': 'ios',
    'android': 'android',
    'ios': 'ios',
    'PLATFORM_TYPE_ANDROID': 'android',
    'PLATFORM_TYPE_IOS': 'ios',
}
```

### Ad Type Mapping
```python
AD_TYPE_MAP = {
    'BANNER': 'banner',
    'INTERSTITIAL': 'interstitial',
    'REWARDED': 'rewarded',
    'REWARDED_VIDEO': 'rewarded',
    'NATIVE': 'banner',  # Native'i banner'a map'le
    'APP_OPEN': 'interstitial',  # App open'ı interstitial'a map'le
}
```

## 🐛 Debug Pratikleri

### Request/Response Logging

Tüm fetcher'larda debug için JSON pretty-print kullanılmalı:

```python
import json

# Request logging
print(f"\n📤 REQUEST:")
print(f"   URL: {url}")
print(f"   Method: POST")
print(f"   Headers: {json.dumps({k: '***' if 'auth' in k.lower() else v for k, v in headers.items()}, indent=2)}")
print(f"   Payload:\n{json.dumps(payload, indent=2)}")

# Response logging
print(f"\n📥 RESPONSE:")
print(f"   Status: {response.status_code}")
print(f"   Body:\n{json.dumps(response.json(), indent=2)[:2000]}")  # İlk 2000 karakter
```

### Error Handling Pattern
```python
try:
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    print(f"\n📥 RESPONSE: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   ❌ Error Response:\n{json.dumps(response.json(), indent=2)}")
        raise Exception(f"API Error: {response.status_code}")
    
    data = response.json()
    print(f"   ✅ Success:\n{json.dumps(data, indent=2)[:1000]}")
    
except requests.exceptions.Timeout:
    print("   ❌ Request timeout")
    raise
except requests.exceptions.RequestException as e:
    print(f"   ❌ Request failed: {e}")
    raise
```

## 📝 Kod Standartları

### Fetcher Sınıfı Yapısı

```python
class NetworkFetcher(NetworkDataFetcher):
    """Network için veri çekici."""
    
    # Class constants
    BASE_URL = "https://api.network.com"
    AD_TYPE_MAP = {...}
    PLATFORM_MAP = {...}
    
    def __init__(self, credentials...):
        """Initialize with credentials."""
        self.credential = credential
        
    def _make_request(self, endpoint, payload) -> Dict:
        """API request wrapper with logging."""
        pass
        
    def _parse_response(self, data) -> Dict:
        """Parse API response to standard format."""
        pass
        
    def fetch_data(self, start_date, end_date) -> Dict:
        """Main method - fetch and return standard format."""
        pass
        
    def get_network_name(self) -> str:
        """Return network name."""
        return "NetworkName"
```

### Docstring Formatı
```python
def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Fetch revenue and impression data for the given date range.
    
    Args:
        start_date: Start date for data fetch
        end_date: End date for data fetch
        
    Returns:
        Dictionary containing revenue and impressions data with platform breakdown
        
    Raises:
        Exception: If API request fails or authentication error
    """
```

## 🔗 Dosya Bağımlılıkları

Yeni network eklerken güncellenecek dosyalar:

| Dosya | Değişiklik |
|-------|-----------|
| `config.yaml` | Network config block ekle |
| `config.yaml.example` | Placeholder config ekle |
| `src/config.py` | `get_networkname_config()` method ekle |
| `src/fetchers/networkname_fetcher.py` | Yeni fetcher class (YENİ) |
| `src/fetchers/__init__.py` | Import ve export ekle |
| `src/validation_service.py` | `NETWORK_NAME_MAP` ve `_initialize_network_fetchers()` güncelle |
| `test_networkname.py` | Test script (YENİ) |

## ⚠️ Önemli Notlar

### Veri Gecikmesi
- Çoğu network 1-3 gün gecikmeyle veri raporlar
- Meta 3 gün gecikmeyle raporlar (ValidationService'de özel handling var)
- Her zaman geçmiş tarihler için veri çek (bugün değil)

### Date Format
- API'ler farklı format kullanır: `YYYY-MM-DD`, ISO 8601, timestamp
- Her zaman UTC timezone kullan
- Tarih aralığı sınırlarına dikkat (inclusive vs exclusive)

### Revenue Scaling
- Bazı API'ler micros döndürür (1,000,000'a böl)
- Bazıları cent döndürür (100'e böl)
- API dokümantasyonunu kontrol et

### Rate Limits
- API rate limit'lerine dikkat et
- Retry logic ekle (429 status code)
- Timeout değerlerini ayarla (30-60 saniye)

## 🚀 Hızlı Başlangıç - Yeni Network

1. `.skills.md` dosyasındaki **"Skill 1: API Döküman Analizi"** ile başla
2. **"Skill 2: Network Fetcher Ekleme"** adımlarını takip et
3. Her adımda terminal çıktısını kontrol et
4. Iteratif olarak düzelt ve test et

---

**Detaylı prosedürler için:** [SKILLS.md](SKILLS.md)
**Şablonlar için:** [templates/](templates/) klasörü
