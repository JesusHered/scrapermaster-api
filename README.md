# ScraperMaster API

Una API avanzada de web scraping que utiliza FastAPI y Playwright para extraer contenido web y convertirlo a markdown de forma organizada y estructurada.

## 🚀 Características

- **Web Scraping Inteligente**: Utiliza Playwright para renderizar páginas dinámicas
- **Conversión a Markdown**: Convierte contenido HTML a markdown limpio y organizado
- **Extracción de Datos**: Detecta automáticamente montos, fechas, contactos y datos estructurados
- **Análisis de Contenido**: Organiza tablas, listas, encabezados e imágenes
- **API RESTful**: Endpoints bien documentados con validación de datos
- **Containerizado**: Listo para deployment con Docker

## 📋 Requisitos

- Python 3.11 o superior
- FastAPI
- Playwright
- BeautifulSoup4
- Docker (opcional)

## 🛠️ Instalación

### Opción 1: Instalación Local

1. Clona este repositorio:

```bash
git clone <repository-url>
cd scrapermaster-api
```

2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

3. Instala los navegadores de Playwright:

```bash
playwright install chromium
```

4. Ejecuta la aplicación:

```bash
uvicorn main:app --reload
```

### Opción 2: Docker

1. Construye la imagen:

```bash
docker build -t scrapermaster-api .
```

2. Ejecuta el contenedor:

```bash
docker run -p 8000:8000 scrapermaster-api
```

### Opción 3: Docker Compose

```bash
docker-compose up --build
```

## Ejecución

### Ejecución Local

Ejecuta el servidor con el siguiente comando:

```bash
uvicorn main:app --reload
```

### Ejecución con Docker

```bash
docker-compose up
```

La API estará disponible en `http://127.0.0.1:8000`.

## Endpoints

- `GET /` - Endpoint principal que devuelve un mensaje de bienvenida
- `GET /.well-known/appspecific/com.chrome.devtools.json` - Configuración para Chrome DevTools

## Documentación de la API

Una vez que la aplicación esté ejecutándose, puedes acceder a:

- **Documentación interactiva (Swagger UI)**: http://127.0.0.1:8000/docs
- **Documentación alternativa (ReDoc)**: http://127.0.0.1:8000/redoc

## 📚 Uso de la API

### Endpoint Principal: POST /scrape

Extrae contenido de una URL y lo convierte a markdown organizado.

**URL**: `http://localhost:8000/scrape`

**Método**: `POST`

**Body**:

```json
{
  "url": "https://example.com"
}
```

**Respuesta**:

```json
{
  "url": "https://example.com",
  "title": "Título de la página",
  "markdown_content": "# Título\n\nContenido en markdown...",
  "metadata": {
    "title": "Título de la página",
    "content_length": 1500,
    "images_count": 5,
    "links_count": 20,
    "amounts_found": 3,
    "has_tables": true,
    "has_lists": true,
    "headings_count": 8
  },
  "images": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.png"
  ],
  "links": [
    {
      "text": "Enlace ejemplo",
      "url": "https://example.com/link"
    }
  ],
  "amounts": ["$1,000.50", "€500.00", "1,200 USD"],
  "structured_data": {
    "tables": [
      [
        ["Header 1", "Header 2"],
        ["Row 1 Col 1", "Row 1 Col 2"]
      ]
    ],
    "lists": [["Item 1", "Item 2", "Item 3"]],
    "headings": {
      "h1": ["Título Principal"],
      "h2": ["Subtítulo 1", "Subtítulo 2"]
    },
    "contact_info": {
      "emails": ["contact@example.com"],
      "phones": ["+1-234-567-8900"]
    },
    "dates": ["2025-06-22", "June 22, 2025"]
  }
}
```

### Otros Endpoints

**GET /health** - Health check de la API

```bash
curl http://localhost:8000/health
```

**GET /** - Endpoint de bienvenida

```bash
curl http://localhost:8000/
```

## 🔧 Ejemplos de Uso

### Ejemplo con cURL

```bash
curl -X POST "http://localhost:8000/scrape" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

### Ejemplo con Python

```python
import requests

response = requests.post(
    "http://localhost:8000/scrape",
    json={"url": "https://example.com"}
)

if response.status_code == 200:
    data = response.json()
    print(f"Título: {data['title']}")
    print(f"Contenido: {data['markdown_content'][:200]}...")
    print(f"Montos encontrados: {data['amounts']}")
```

### Ejemplo con JavaScript

```javascript
fetch("http://localhost:8000/scrape", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    url: "https://example.com",
  }),
})
  .then((response) => response.json())
  .then((data) => {
    console.log("Título:", data.title);
    console.log("Contenido:", data.markdown_content);
    console.log("Montos:", data.amounts);
  });
```

## 🎯 Características del Procesamiento

### Extracción Inteligente

- **Montos y Cantidades**: Detecta automáticamente precios, cantidades y valores monetarios
- **Fechas**: Identifica fechas en múltiples formatos
- **Contactos**: Extrae emails y números de teléfono
- **Estructura**: Organiza tablas, listas y encabezados

### Limpieza de Contenido

- Elimina elementos innecesarios (scripts, estilos, navegación)
- Prioriza contenido principal (main, article)
- Convierte a markdown limpio y legible

### Optimizado para LLM

- Estructura jerárquica clara
- Datos organizados en categorías
- Formato markdown estándar
- Metadatos descriptivos

## 🐳 Docker

El proyecto incluye configuración completa de Docker con:

- Instalación automática de dependencias del sistema
- Configuración de Playwright y navegadores
- Optimización para contenedores

## 📝 Desarrollo

Para ejecutar en modo desarrollo:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Para probar la API:

```bash
python test_api.py
```

## 📄 Documentación API

La documentación interactiva está disponible en:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔒 Seguridad

- Validación estricta de URLs
- Timeout configurado para peticiones
- Sanitización de contenido HTML
- Límites en cantidad de datos extraídos

## 🚀 Deployment

Para producción, considera:

- Variables de entorno para configuración
- Proxy reverso (nginx)
- Monitoreo y logs
- Escalado horizontal

## 📞 Soporte

Para reportar bugs o solicitar características, crea un issue en el repositorio.
