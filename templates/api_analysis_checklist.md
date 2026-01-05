# API Analiz Checklist - [Network Adı]

> Bu checklist'i API dökümanını analiz ederken doldurun.
> Doldurulduktan sonra fetcher implementasyonu için referans olarak kullanılacak.

---

## 📋 Temel Bilgiler

| Alan | Değer |
|------|-------|
| **Network Adı** | |
| **API Döküman URL** | |
| **API Versiyonu** | |
| **Analiz Tarihi** | |

---

## 1️⃣ Endpoint Yapısı

### Base URL
```
□ Base URL: 
```

### Report Endpoint
```
□ Path: 
□ HTTP Method: □ GET  □ POST
□ Content-Type: □ JSON  □ Form Data  □ Query Params
```

### Auth Endpoint (varsa)
```
□ Path: 
□ HTTP Method: □ GET  □ POST
```

---

## 2️⃣ Authentication

### Auth Tipi
```
□ API Key (Header)
□ API Key (Query Param)
□ Bearer Token
□ OAuth 2.0
□ Basic Auth
□ Session-based (Login → Token)
□ HMAC/Signature
```

### Auth Detayları
```
Header Adı: 
Header Format: 
Token Süresi: 
Refresh Endpoint: 
```

### Örnek Auth Header
```
Authorization: Bearer {token}
X-API-Key: {api_key}
```

---

## 3️⃣ Request Formatı

### Zorunlu Parametreler
| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| | | |
| | | |
| | | |

### Opsiyonel Parametreler
| Parametre | Tip | Açıklama |
|-----------|-----|----------|
| | | |
| | | |

### Tarih Formatı
```
□ YYYY-MM-DD
□ YYYY-MM-DDTHH:MM:SSZ (ISO 8601)
□ Unix timestamp (seconds)
□ Unix timestamp (milliseconds)
□ Diğer: 
```

### Tarih Aralığı Parametreleri
```
□ start_date / end_date
□ date_range: {start, end}
□ since / until
□ from / to
□ Diğer: 
```

### Örnek Request Body
```json
{

}
```

---

## 4️⃣ Response Yapısı

### Response Formatı
```
□ JSON Object
□ JSON Array
□ CSV
□ Streaming
```

### Data Konumu
```
□ Root level (response = [...])
□ data key (response.data)
□ rows key (response.rows)
□ results key (response.results)
□ Diğer: 
```

### Pagination
```
□ Yok
□ Offset-based (offset, limit)
□ Cursor-based (next_cursor)
□ Page-based (page, per_page)
□ Token-based (next_page_token)
```

### Async Response
```
□ Hayır - Hemen sonuç döner
□ Evet - Job ID döner, poll etmek gerekir
   Poll Endpoint: 
   Poll Interval: 
```

### Örnek Response
```json
{

}
```

---

## 5️⃣ Alan Mapping

### Revenue
| API Field | Örnek Değer | Birim | Scale |
|-----------|-------------|-------|-------|
| | | □ USD □ Micros □ Cents | |

### Impressions
| API Field | Örnek Değer | Tip |
|-----------|-------------|-----|
| | | □ int □ string |

### Platform
| API Field | Örnek Değerler |
|-----------|----------------|
| | |

**Platform Mapping:**
| API Değeri | Standard Değer |
|------------|----------------|
| | android |
| | android |
| | ios |
| | ios |

### Ad Type
| API Field | Örnek Değerler |
|-----------|----------------|
| | |

**Ad Type Mapping:**
| API Değeri | Standard Değer |
|------------|----------------|
| | banner |
| | interstitial |
| | rewarded |
| | rewarded |

---

## 6️⃣ Kısıtlamalar

### Rate Limits
```
□ Requests per minute: 
□ Requests per hour: 
□ Requests per day: 
□ Concurrent requests: 
```

### Date Range Limits
```
□ Maximum gün: 
□ Geriye dönük limit: 
```

### Data Availability
```
□ Real-time
□ 1 gün gecikme
□ 2 gün gecikme
□ 3+ gün gecikme: 
```

---

## 7️⃣ Hata Kodları

| Status Code | Anlam | Aksiyon |
|-------------|-------|---------|
| 401 | Unauthorized | Token/Key kontrol |
| 403 | Forbidden | Permission kontrol |
| 429 | Rate Limited | Retry with backoff |
| | | |

---

## 8️⃣ Ek Notlar

### Özel Durumlar
```




```

### Dikkat Edilecekler
```




```

---

## ✅ Analiz Tamamlandı

```
□ Endpoint yapısı anlaşıldı
□ Auth mekanizması anlaşıldı
□ Request formatı belirlendi
□ Response yapısı analiz edildi
□ Field mapping tamamlandı
□ Kısıtlamalar not edildi
□ Fetcher implementasyonuna hazır
```

---

**Sonraki Adım:** `.skills.md` dosyasındaki "Skill 2: Network Fetcher Ekleme" prosedürünü takip et.
