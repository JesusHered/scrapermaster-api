from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import json
import asyncio
from typing import Dict, List, Optional
from markdownify import markdownify as md
import os
import base64

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Modelos Pydantic
class UrlRequest(BaseModel):
    url: HttpUrl

class ScrapedContent(BaseModel):
    url: str
    title: str
    markdown_content: str
    metadata: Dict
    images: List[str]
    links: List[Dict[str, str]]
    amounts: List[str]
    structured_data: Dict

class ContentProcessor:
    """Clase para procesar y estructurar el contenido extraído"""
    
    @staticmethod
    def extract_amounts(text: str) -> List[str]:
        """Extrae montos y cantidades del texto"""
        amount_patterns = [
            r'\$[\d,]+\.?\d*',  # Dólares: $1,000.50
            r'€[\d,]+\.?\d*',   # Euros: €1,000.50
            r'£[\d,]+\.?\d*',   # Libras: £1,000.50
            r'[\d,]+\.?\d*\s*(?:USD|EUR|GBP|MXN|ARS|COP|PEN|CLP)',  # Cantidades con moneda
            r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b',  # Números con formato de moneda
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            amounts.extend(matches)
        
        return list(set(amounts))  # Remover duplicados
    
    @staticmethod
    def extract_structured_data(soup: BeautifulSoup) -> Dict:
        """Extrae datos estructurados como tablas, listas, etc."""
        structured = {
            "tables": [],
            "lists": [],
            "headings": {},
            "contact_info": [],
            "dates": []
        }
        
        # Extraer tablas
        tables = soup.find_all('table')
        for table in tables:
            rows = []
            for tr in table.find_all('tr'):
                row = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if row:
                    rows.append(row)
            if rows:
                structured["tables"].append(rows)
        
        # Extraer listas
        for ul in soup.find_all(['ul', 'ol']):
            items = [li.get_text(strip=True) for li in ul.find_all('li')]
            if items:
                structured["lists"].append(items)
        
        # Extraer encabezados
        for i in range(1, 7):
            headings = soup.find_all(f'h{i}')
            if headings:
                structured["headings"][f"h{i}"] = [h.get_text(strip=True) for h in headings]
        
        # Extraer información de contacto
        text = soup.get_text()
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'[\+]?[1-9]?[\d\s\-\(\)]{7,15}'
        
        emails = re.findall(email_pattern, text)
        phones = re.findall(phone_pattern, text)
        
        structured["contact_info"] = {
            "emails": list(set(emails)),
            "phones": list(set(phones))
        }
        
        # Extraer fechas
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY o MM/DD/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY/MM/DD
            r'\b(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        structured["dates"] = list(set(dates))
        
        return structured
    
    @staticmethod
    def clean_and_organize_content(html_content: str) -> str:
        """Limpia y organiza el contenido HTML antes de convertir a markdown"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remover elementos no deseados
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Mejorar la estructura
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile('content|main|article'))
        
        if main_content:
            return str(main_content)
        else:
            return str(soup)

async def scrape_url_content(url: str) -> ScrapedContent:
    """Extrae contenido de una URL usando Playwright"""
    try:
        async with async_playwright() as p:
            # Usar Chromium con configuración optimizada
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            page = await context.new_page()
            
            # Navegar a la URL con timeout
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Esperar a que la página se cargue completamente
            await page.wait_for_timeout(2000)
            
            # Extraer información básica
            title = await page.title()
            
            # Extraer todo el contenido HTML
            html_content = await page.content()
            
            # Extraer enlaces de imágenes
            images = await page.evaluate('''
                () => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs.map(img => {
                        const src = img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src');
                        return src;
                    }).filter(src => src && src.startsWith('http'));
                }
            ''')
            
            # Extraer enlaces
            links = await page.evaluate('''
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(link => ({
                        text: link.textContent.trim(),
                        url: link.href
                    })).filter(link => link.text && link.url);
                }
            ''')
            
            await browser.close()
            
            # Procesar el contenido
            processor = ContentProcessor()
            
            # Limpiar y organizar HTML
            clean_html = processor.clean_and_organize_content(html_content)
            
            # Convertir a markdown
            markdown_content = md(clean_html, heading_style="ATX")
            
            # Crear objeto BeautifulSoup para análisis adicional
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extraer montos
            amounts = processor.extract_amounts(soup.get_text())
            
            # Extraer datos estructurados
            structured_data = processor.extract_structured_data(soup)
            
            # Crear metadata
            metadata = {
                "title": title,
                "content_length": len(markdown_content),
                "images_count": len(images),
                "links_count": len(links),
                "amounts_found": len(amounts),
                "has_tables": len(structured_data["tables"]) > 0,
                "has_lists": len(structured_data["lists"]) > 0,
                "headings_count": sum(len(headings) for headings in structured_data["headings"].values())
            }
            
            return ScrapedContent(
                url=url,
                title=title,
                markdown_content=markdown_content,
                metadata=metadata,
                images=images[:20],  # Limitar a 20 imágenes
                links=links[:50],    # Limitar a 50 enlaces
                amounts=amounts,
                structured_data=structured_data
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la URL: {str(e)}")

async def capture_screenshots_playwright(url: str, output_dir: str) -> Dict[str, str]:
    """Captura capturas de pantalla de toda la página usando Playwright."""
    screenshots_base64 = {}
    
    try:
        async with async_playwright() as p:
            # Usar Chromium con configuración optimizada
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            # Navegar a la URL
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Esperar a que la página se cargue completamente
            await page.wait_for_load_state('networkidle')
            
            # Capturar pantalla completa
            full_screenshot = await page.screenshot(full_page=True, type='png')
            screenshots_base64['full_screenshot'] = base64.b64encode(full_screenshot).decode('utf-8')
            
            # Capturar screenshot del viewport actual
            viewport_screenshot = await page.screenshot(type='png')
            screenshots_base64['viewport_screenshot'] = base64.b64encode(viewport_screenshot).decode('utf-8')
            
            # Capturar screenshots de elementos específicos si existen
            try:
                # Capturar header si existe
                header = page.locator('header, .header, #header').first
                if await header.count() > 0:
                    header_screenshot = await header.screenshot(type='png')
                    screenshots_base64['header'] = base64.b64encode(header_screenshot).decode('utf-8')
                
                # Capturar main content si existe
                main = page.locator('main, .main, #main, .content, #content').first
                if await main.count() > 0:
                    main_screenshot = await main.screenshot(type='png')
                    screenshots_base64['main_content'] = base64.b64encode(main_screenshot).decode('utf-8')
                
                # Capturar footer si existe
                footer = page.locator('footer, .footer, #footer').first
                if await footer.count() > 0:
                    footer_screenshot = await footer.screenshot(type='png')
                    screenshots_base64['footer'] = base64.b64encode(footer_screenshot).decode('utf-8')
                
            except Exception as e:
                print(f"Error capturando elementos específicos: {e}")
            
            await browser.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error capturando screenshots: {str(e)}")
    
    return screenshots_base64

@app.post("/screenshots")
async def get_screenshots(url_request: UrlRequest):
    """Endpoint para capturar capturas de pantalla y devolverlas en Base64."""
    url = str(url_request.url)
    
    # Validar que la URL sea accesible
    if not url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="URL debe comenzar con http:// o https://")
    
    try:
        # Capturar las capturas de pantalla usando Playwright
        screenshots_base64 = await capture_screenshots_playwright(url, "./screenshots")
        
        # Retornar las capturas en Base64
        return JSONResponse(content={
            "url": url,
            "screenshots": screenshots_base64,
            "total_screenshots": len(screenshots_base64)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error capturando screenshots: {str(e)}")

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

@app.post("/scrape", response_model=ScrapedContent)
async def scrape_url(request: UrlRequest):
    """
    Endpoint POST para extraer contenido de una URL y convertirlo a markdown organizado.
    
    - **url**: URL del sitio web a procesar
    
    Retorna:
    - Contenido en markdown organizado
    - Metadatos de la página
    - URLs de imágenes encontradas
    - Enlaces extraídos
    - Montos y cantidades detectadas
    - Datos estructurados (tablas, listas, encabezados, etc.)
    """
    url_str = str(request.url)
    
    # Validar que la URL sea accesible
    if not url_str.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="URL debe comenzar con http:// o https://")
    
    try:
        result = await scrape_url_content(url_str)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando la URL: {str(e)}")

@app.get("/health")
def health_check():
    """Endpoint para verificar el estado de la API"""
    return {"status": "healthy", "message": "ScraperMaster API está funcionando correctamente"}
