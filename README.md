# Medya Takip Merkezi - Vector Database

Qdrant tabanlı semantik arama ve doküman yönetimi platformu.

## 🚀 Hızlı Başlangıç

```bash
# Sunucunuzda projeyi klonlayın veya dosyaları aktarın
cd mtm-vector-db

# Servisleri başlatın
docker compose up -d

# Durumu kontrol edin
docker compose ps
```

## 🌐 Erişim

| Servis | URL | Açıklama |
|--------|-----|----------|
| Web Arayüzü | http://localhost | Ana uygulama |
| API Docs | http://localhost/api/docs | Swagger UI |
| Qdrant Dashboard | http://localhost:6333/dashboard | Veritabanı yönetimi |

## 📁 Proje Yapısı

```
mtm-vector-db/
├── docker-compose.yml      # Servis tanımları
├── backend/                # FastAPI backend
│   ├── main.py            # Ana uygulama
│   ├── models.py          # Veri modelleri
│   ├── services/          # Qdrant & Embedding servisleri
│   └── routers/           # API endpoint'leri
├── frontend/              # Web arayüzü
│   ├── index.html
│   ├── css/style.css
│   └── js/
└── nginx/                 # Reverse proxy
```

## 📝 API Kullanımı

### Doküman Ekleme
```bash
curl -X POST http://localhost/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Örnek Haber",
    "content": "Haber içeriği...",
    "source": "https://example.com",
    "category": "ekonomi"
  }'
```

### Semantik Arama
```bash
curl -X POST http://localhost/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "ekonomi haberleri", "limit": 10}'
```

### Toplu Yükleme (JSON)
```bash
curl -X POST http://localhost/api/documents/bulk \
  -H "Content-Type: application/json" \
  -d '{"documents": [...]}'
```

## 📦 Örnek Veri

`sample-data.json` dosyasını kullanarak test verisi yükleyebilirsiniz:

```bash
curl -X POST http://localhost/api/documents/bulk \
  -H "Content-Type: application/json" \
  -d @sample-data.json
```

## 🔧 Ayarlar

Ortam değişkenleri (`docker-compose.yml`):
- `QDRANT_HOST`: Qdrant sunucu adresi
- `QDRANT_PORT`: Qdrant port (varsayılan: 6333)
- `COLLECTION_NAME`: Koleksiyon adı (varsayılan: medya_takip)

## 🤖 İleride AI Entegrasyonu

Sistem, local LLM entegrasyonuna hazır. Ollama veya benzeri bir servis eklenebilir:

```yaml
# docker-compose.yml'e eklenebilir
ollama:
  image: ollama/ollama
  ports:
    - "11434:11434"
```

## 📊 Özellikler

- ✅ Semantik arama (Türkçe destekli)
- ✅ Doküman CRUD işlemleri
- ✅ Toplu veri yükleme
- ✅ İlişki grafiği görselleştirmesi
- ✅ Kategori ve kaynak filtreleme
- ✅ Modern dark theme arayüz
