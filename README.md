# Scrapermaster API

Este proyecto utiliza FastAPI para crear una API básica.

## Requisitos

- Python 3.9 o superior
- FastAPI
- Uvicorn

## Instalación

### Opción 1: Instalación Local

1. Clona este repositorio.
2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

### Opción 2: Usando Docker

1. Clona este repositorio.
2. Construye y ejecuta con Docker Compose:

```bash
docker-compose up --build
```

O usando Docker directamente:

```bash
# Construir la imagen
docker build -t scrapermaster-api .

# Ejecutar el contenedor
docker run -p 8000:8000 scrapermaster-api
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