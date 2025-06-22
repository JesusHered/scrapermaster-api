from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_config():
    """Endpoint para configuración de Chrome DevTools"""
    return JSONResponse(content={
        "name": "ScraperMaster API",
        "version": "1.0.0",
        "description": "API para scraping de datos",
        "devtools": {
            "enabled": True,
            "debuggingPort": 9229
        }
    })

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}
