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
├── main.py                    # Ana giriş noktası (asyncio.run)
├── config.yaml                # Aktif konfigürasyon (gitignore'da)
├── config.yaml.example        # Örnek konfigürasyon
├── requirements.txt           # Python bağımlılıkları
├── credentials/               # OAuth token'ları ve cache (gitignore'da)
├── templates/                 # Yeni bileşen şablonları
│   ├── network_fetcher_template.py
│   ├── test_network_template.py
│   └── api_analysis_checklist.md
├── src/
│   ├── config.py              # Konfigürasyon yöneticisi
│   ├── enums.py               # Platform, AdType, NetworkName enum'ları
│   ├── validation_service.py  # Ana async orkestrasyon servisi
│   ├── fetchers/              # Network veri çekicileri (async)
│   │   ├── base_fetcher.py    # Abstract base class (aiohttp, retry, helpers)
│   │   ├── applovin_fetcher.py
│   │   ├── admob_fetcher.py
│   │   ├── meta_fetcher.py
│   │   ├── moloco_fetcher.py
│   │   ├── mintegral_fetcher.py
│   │   ├── unity_fetcher.py
│   │   ├── ironsource_fetcher.py
│   │   ├── inmobi_fetcher.py
│   │   ├── bidmachine_fetcher.py
│   │   ├── liftoff_fetcher.py
│   │   ├── dt_exchange_fetcher.py
│   │   ├── pangle_fetcher.py
│   │   └── __init__.py        # Export'lar
│   ├── utils/                 # Yardımcı modüller
│   │   ├── token_cache.py     # File-based token caching
│   │   └── __init__.py
│   ├── exporters/             # Veri export servisleri
│   │   ├── gcs_exporter.py    # GCS/BigQuery export
│   │   └── __init__.py
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
│              ValidationService (async)                           │
│                    │         │                                   │
│          ┌────────┴─────────┴────────┐                          │
│          ▼                           ▼                          │
│   ApplovinFetcher              NetworkFetchers                  │
│   (MAX baseline)               (asyncio.gather ile paralel)     │
│   (async fetch)                (moloco, meta, etc.)             │
│          │                           │                          │
│          └───────────┬───────────────┘                          │
│                      ▼                                          │
│               DataValidator                                     │
│              (compare metrics)                                  │
│                      │                                          │
│                      ▼                                          │
│              SlackNotifier + GCSExporter                        │
│            (Slack alerts & BigQuery export)                     │
└─────────────────────────────────────────────────────────────────┘
```

### ⚡ Paralel Fetching (Performans Optimizasyonu)

Tüm network'ler `asyncio.gather()` ile paralel çekilir:
- Sıralı: ~30-60 saniye (12 network × 3-5s)
- Paralel: ~5-8 saniye

```python
async def _fetch_all_networks_parallel(self, ...):
    tasks = [
        fetch_network(name, fetcher)
        for name, fetcher in self.network_fetchers.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

## 📊 Standart Veri Yapısı

### FetchResult Type (TypedDict)

Tüm fetcher'lar `FetchResult` tipinde veri döndürür:

```python
from src.fetchers.base_fetcher import FetchResult

result: FetchResult = {
    'revenue': float,           # Toplam gelir (USD)
    'impressions': int,         # Toplam gösterim
    'ecpm': float,              # (revenue / impressions) * 1000
    'network': str,             # Network adı (NetworkName.MOLOCO.display_name)
    'date_range': {
        'start': 'YYYY-MM-DD',
        'end': 'YYYY-MM-DD'
    },
    'ad_data': {                # Toplam ad type breakdown
        'banner': {'revenue': float, 'impressions': int, 'ecpm': float},
        'interstitial': {'revenue': float, 'impressions': int, 'ecpm': float},
        'rewarded': {'revenue': float, 'impressions': int, 'ecpm': float}
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

### Enum Kullanımı

```python
from src.enums import Platform, AdType, NetworkName

# Platform enum
platform = Platform.from_string('Android')  # Platform.ANDROID
platform.value  # 'android'
platform.display_name  # 'Android'

# AdType enum  
ad_type = AdType.from_string('rewarded_video')  # AdType.REWARDED
ad_type.value  # 'rewarded'

# NetworkName enum
network = NetworkName.from_api_name('MOLOCO_BIDDING')  # NetworkName.MOLOCO
network.value  # 'moloco'
network.display_name  # 'Moloco Bidding'
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

### 3. Session-based (Login → Token) + Token Cache
```python
# TokenCache ile token'lar file-based cache'lenir (55-60 dk TTL)
from src.utils import TokenCache

class MolocoFetcher(NetworkDataFetcher):
    TOKEN_CACHE_KEY = "moloco"
    TOKEN_EXPIRES_IN = 3300  # 55 minutes
    
    def __init__(self, ...):
        super().__init__()
        self._token_cache = TokenCache()
    
    async def _get_access_token(self) -> str:
        # Check cache first
        cached = self._token_cache.get_token(self.TOKEN_CACHE_KEY)
        if cached:
            return cached['token']
        
        # Fetch new token
        data = await self._post_json(AUTH_URL, json={...})
        token = data['token']
        
        # Save to cache
        self._token_cache.save_token(
            self.TOKEN_CACHE_KEY,
            token,
            expires_in=self.TOKEN_EXPIRES_IN
        )
        return token
```

## 🗺️ Platform ve Ad Type Mapping

### ⚠️ Enum Kullanımı (Zorunlu)

Tüm fetcher'lar artık string yerine enum kullanmalıdır:

```python
from src.enums import Platform, AdType, NetworkName
```

### Platform Mapping (Enum)
```python
# Fetcher'da tanımlama
PLATFORM_MAP = {
    'ANDROID': Platform.ANDROID,
    'IOS': Platform.IOS,
    'android': Platform.ANDROID,
    'ios': Platform.IOS,
    'PLATFORM_TYPE_ANDROID': Platform.ANDROID,
    'PLATFORM_TYPE_IOS': Platform.IOS,
}

# Veya base_fetcher'daki helper kullanımı
platform = self._normalize_platform('Android')  # Platform.ANDROID
```

### Ad Type Mapping (Enum)
```python
# Fetcher'da tanımlama
AD_TYPE_MAP = {
    'BANNER': AdType.BANNER,
    'INTERSTITIAL': AdType.INTERSTITIAL,
    'REWARDED': AdType.REWARDED,
    'REWARDED_VIDEO': AdType.REWARDED,
    'NATIVE': AdType.BANNER,        # Native'i banner'a map'le
    'APP_OPEN': AdType.INTERSTITIAL,  # App open'ı interstitial'a map'le
}

# Veya base_fetcher'daki helper kullanımı
ad_type = self._normalize_ad_type('rewarded_video')  # AdType.REWARDED
```

### Network Name Mapping (Enum)
```python
# validation_service.py'de kullanım
network_key = NetworkName.from_api_name('MOLOCO_BIDDING')  # NetworkName.MOLOCO
network_key.value  # 'moloco' (fetcher dict key)
network_key.display_name  # 'Moloco Bidding' (Slack'te gösterilir)
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

### Fetcher Sınıfı Yapısı (Async)

```python
from src.fetchers.base_fetcher import NetworkDataFetcher, FetchResult
from src.enums import Platform, AdType, NetworkName

class NetworkFetcher(NetworkDataFetcher):
    """Network için async veri çekici."""
    
    # Class constants
    BASE_URL = "https://api.network.com"
    
    # Enum-based mappings
    AD_TYPE_MAP = {
        'BANNER': AdType.BANNER,
        'REWARDED': AdType.REWARDED,
        ...
    }
    PLATFORM_MAP = {
        'ANDROID': Platform.ANDROID,
        'IOS': Platform.IOS,
        ...
    }
    
    def __init__(self, credentials...):
        """Initialize with credentials."""
        super().__init__()  # ⚠️ Zorunlu - aiohttp session oluşturur
        self.credential = credential
        
    async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
        """Main async method - fetch and return standard format."""
        # Base class helpers kullan
        ad_data = self._init_ad_data()
        platform_data = self._init_platform_data()
        
        # Async request (base class'dan)
        data = await self._get_json(url, headers=headers, params=params)
        # veya
        data = await self._post_json(url, headers=headers, json=payload)
        
        # Metric accumulation (base class helper)
        self._accumulate_metrics(
            platform_data, ad_data,
            Platform.ANDROID, AdType.REWARDED,
            revenue, impressions
        )
        
        # Build result (base class helper)
        result = self._build_result(
            start_date, end_date,
            revenue=total_revenue,
            impressions=total_impressions,
            ad_data=ad_data,
            platform_data=platform_data
        )
        
        # Finalize eCPMs
        self._finalize_ecpm(result, ad_data, platform_data)
        
        return result
        
    def get_network_name(self) -> str:
        """Return network display name."""
        return NetworkName.NETWORK.display_name
    
    def get_network_enum(self) -> NetworkName:
        """Return NetworkName enum."""
        return NetworkName.NETWORK
```

### Docstring Formatı
```python
async def fetch_data(self, start_date: datetime, end_date: datetime) -> FetchResult:
    """
    Fetch revenue and impression data for the given date range.
    
    Uses aiohttp for async HTTP requests with retry support.
    
    Args:
        start_date: Start date for data fetch
        end_date: End date for data fetch
        
    Returns:
        FetchResult containing revenue and impressions data with platform breakdown
        
    Raises:
        aiohttp.ClientError: If HTTP request fails
        Exception: If API returns error or authentication fails
    """
```

## 🔗 Dosya Bağımlılıkları

Yeni network eklerken güncellenecek dosyalar:

| Dosya | Değişiklik |
|-------|-----------|
| `config.yaml` | Network config block ekle |
| `config.yaml.example` | Placeholder config ekle |
| `src/config.py` | `get_networkname_config()` method ekle |
| `src/enums.py` | `NetworkName` enum'a yeni network ekle |
| `src/fetchers/networkname_fetcher.py` | Yeni async fetcher class (YENİ) |
| `src/fetchers/__init__.py` | Import ve export ekle |
| `src/validation_service.py` | `_initialize_network_fetchers()` güncelle |
| `test_networkname.py` | Async test script (YENİ) |

### ⚠️ Önemli: Artık NETWORK_NAME_MAP güncellenmiyor

Network name mapping artık `src/enums.py` içindeki `NetworkName.from_api_name()` metodunda tanımlı. Yeni network eklerken:

```python
# src/enums.py - NetworkName.from_api_name() içine ekle
'NEWNETWORK_BIDDING': cls.NEWNETWORK,
'NEWNETWORK': cls.NEWNETWORK,
'NewNetwork Bidding': cls.NEWNETWORK,
'NewNetwork': cls.NEWNETWORK,
```

## ⚠️ Önemli Notlar

### Async/Await (Zorunlu)
- Tüm fetcher'lar `async def fetch_data()` kullanmalı
- `requests` yerine base class'ın `_get_json()` ve `_post_json()` metodları kullanılmalı
- `super().__init__()` çağrısı zorunlu (aiohttp session oluşturur)
- Test scriptleri `asyncio.run()` ile çalıştırılmalı

### Enum Kullanımı (Zorunlu)
- String yerine `Platform`, `AdType`, `NetworkName` enum'ları kullanılmalı
- Base class helper'ları enum döndürür: `_normalize_platform()`, `_normalize_ad_type()`
- `get_network_enum()` metodu eklenmeli

### Veri Gecikmesi
- Çoğu network 1-3 gün gecikmeyle veri raporlar
- Meta 1 gün gecikmeyle raporlar (DATA_DELAY_DAYS = 1)
- Her zaman geçmiş tarihler için veri çek (bugün değil)

### Date Format
- API'ler farklı format kullanır: `YYYY-MM-DD`, ISO 8601, timestamp
- Her zaman UTC timezone kullan
- Tarih aralığı sınırlarına dikkat (inclusive vs exclusive)

### Revenue Scaling
- Bazı API'ler micros döndürür (1,000,000'a böl)
- Bazıları cent döndürür (100'e böl)
- API dokümantasyonunu kontrol et

### Rate Limits & Retry
- Base class'ta otomatik retry desteği var (tenacity)
- API rate limit'lerine dikkat et
- Timeout değerleri base class'ta ayarlanmış (30s default)

## 🚀 Hızlı Başlangıç - Yeni Network

1. `.skills.md` dosyasındaki **"Skill 1: API Döküman Analizi"** ile başla
2. **"Skill 2: Network Fetcher Ekleme"** adımlarını takip et
3. Her adımda terminal çıktısını kontrol et
4. Iteratif olarak düzelt ve test et

---

**Detaylı prosedürler için:** [SKILLS.md](SKILLS.md)
**Şablonlar için:** [templates/](templates/) klasörü
