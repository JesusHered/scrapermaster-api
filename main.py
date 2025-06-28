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
    clean_body_html: str
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
        phone_pattern = r'(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}|\+?[1-9][0-9]{1,3}[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{2,4}'
        
        emails = re.findall(email_pattern, text)
        phones = [phone.strip() for phone in re.findall(phone_pattern, text) if phone.strip() and not phone.strip().isspace() and len(phone.strip()) > 6 and any(c.isdigit() for c in phone)]
        
        # Extraer nombres de contactos (patrones comunes)
        name_patterns = [
            r'\b(?:Contact|Contacto|Contact Person|Contact Name):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'\b(?:Name|Nombre):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s*,\s*(?:Director|Manager|CEO|President|VP)',
            r'\b(?:Dr\.|Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]
        
        contact_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            contact_names.extend(matches)
        
        structured["contact_info"] = {
            "emails": list(set(emails)),
            "phones": list(set(phones)),
            "names": list(set(contact_names))
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
            try:
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
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al iniciar el navegador: {str(e)}")
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    locale='en-US',  # Establecer idioma como inglés americano
                    timezone_id='America/New_York'  # Usar zona horaria estadounidense para coherencia
                )
                
                page = await context.new_page()
            except Exception as e:
                await browser.close()
                raise HTTPException(status_code=500, detail=f"Error al crear contexto del navegador: {str(e)}")
            
            try:
                # Navegar a la URL con timeout
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            except asyncio.TimeoutError:
                await browser.close()
                raise HTTPException(status_code=504, detail="Tiempo de espera agotado al cargar la página")
            except Exception as e:
                await browser.close()
                raise HTTPException(status_code=500, detail=f"Error al navegar a la URL: {str(e)}")
            
            # Intentar manejar diálogos de cookies comunes
            try:
                await handle_cookie_dialogs(page)
            except Exception as e:
                print(f"Advertencia: Error al manejar diálogos de cookies: {str(e)}")
                # No fallamos por esto, continuamos con el proceso
            
            # Esperar a que la página se cargue completamente (5 segundos)
            await page.wait_for_timeout(5000)
            
            try:
                # Extraer información básica
                title = await page.title()
                
                # Extraer todo el contenido HTML
                html_content = await page.content()
            except Exception as e:
                await browser.close()
                raise HTTPException(status_code=500, detail=f"Error al extraer contenido básico de la página: {str(e)}")
            
            # Esperar 5 segundos adicionales antes de comenzar el scraping (solicitado por el usuario)
            await page.wait_for_timeout(5000)
            
            try:
                # Extraer enlaces de imágenes (todas las imágenes, no solo las primeras 20)
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
            except Exception as e:
                await browser.close()
                raise HTTPException(status_code=500, detail=f"Error al extraer imágenes y enlaces: {str(e)}")
            
            await browser.close()
            
            # Procesar el contenido
            try:
                processor = ContentProcessor()
                
                # Limpiar y organizar HTML
                clean_html = processor.clean_and_organize_content(html_content)
                
                # Convertir a markdown
                markdown_content = md(clean_html, heading_style="ATX")
                
                # Crear objeto BeautifulSoup para análisis adicional
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extraer HTML del body sin scripts ni estilos
                body_soup = soup.find('body')
                if body_soup:
                    # Eliminar scripts y estilos
                    for tag in body_soup(['script', 'style']):
                        tag.decompose()
                    clean_body_html = str(body_soup)
                else:
                    clean_body_html = ""
                
                # Extraer emails
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = list(set(re.findall(email_pattern, soup.get_text())))
                
                # Extraer números de teléfono
                phone_pattern = r'(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}|\+?[1-9][0-9]{1,3}[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{2,4}[-.\s]?[0-9]{2,4}'
                phones = [phone.strip() for phone in re.findall(phone_pattern, soup.get_text()) if phone.strip() and not phone.strip().isspace() and len(phone.strip()) > 6 and any(c.isdigit() for c in phone)]
                
                # Extraer montos
                amounts = processor.extract_amounts(soup.get_text())
                
                # Extraer datos estructurados
                structured_data = processor.extract_structured_data(soup)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error al procesar el contenido HTML: {str(e)}")
            
            # Crear metadata
            metadata = {
                "title": title,
                "content_length": len(markdown_content),
                "images_count": len(images),
                "links_count": len(links),
                "amounts_found": len(amounts),
                "has_tables": len(structured_data["tables"]) > 0,
                "has_lists": len(structured_data["lists"]) > 0,
                "headings_count": sum(len(headings) for headings in structured_data["headings"].values()),
                "emails_found": len(emails),
                "phones_found": len(phones)
            }
            
            return ScrapedContent(
                url=url,
                title=title,
                markdown_content=markdown_content,
                clean_body_html=clean_body_html,
                metadata=metadata,
                images=images,  # Ya no limitamos a 20 imágenes
                links=links[:50],    # Limitar a 50 enlaces
                amounts=amounts,
                structured_data={
                    **structured_data,
                    "emails": emails,
                    "phones": phones
                }
            )
            
    except HTTPException as e:
        # Re-lanzar excepciones HTTP ya formateadas
        raise e
    except Exception as e:
        print(f"Error no controlado en scrape_url_content: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado al procesar la URL: {str(e)}")

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
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',  # Establecer idioma como inglés americano
                timezone_id='America/New_York'  # Usar zona horaria estadounidense para coherencia
            )
            
            page = await context.new_page()
            
            # Navegar a la URL
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Esperar a que la página se cargue completamente
            await page.wait_for_load_state('networkidle')
            
            # Intentar manejar diálogos de cookies comunes
            await handle_cookie_dialogs(page)
            
            # Esperar 5 segundos adicionales para asegurar que todo el contenido dinámico esté cargado
            await page.wait_for_timeout(5000)
            
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
        
    except HTTPException as e:
        # Re-lanzar excepciones HTTP ya formateadas
        raise e
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Tiempo de espera agotado al capturar screenshots de: {url}. La página tardó demasiado en responder.")
    except Exception as e:
        # Obtener información detallada del error
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Crear mensaje de error detallado basado en el tipo de error
        if "Playwright" in error_type or "Browser" in error_type:
            error_detail = f"Error en el navegador al capturar screenshots de {url}: {error_msg}"
        elif "Connection" in error_type or "Network" in error_type:
            error_detail = f"Error de conexión al acceder a {url} para capturas: {error_msg}"
        elif "SSL" in error_type:
            error_detail = f"Error de seguridad SSL al acceder a {url}: {error_msg}"
        else:
            error_detail = f"Error inesperado al capturar screenshots de {url}: {error_type} - {error_msg}"
        
        # Registrar el error para depuración
        print(f"ERROR en /screenshots: {error_detail}")
        
        # Devolver respuesta de error detallada
        raise HTTPException(status_code=500, detail=error_detail)

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
    except HTTPException as e:
        # Re-lanzar excepciones HTTP ya formateadas
        raise e
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Tiempo de espera agotado al procesar la URL: {url_str}. La página tardó demasiado en responder.")
    except Exception as e:
        # Obtener información detallada del error
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Crear mensaje de error detallado basado en el tipo de error
        if "Playwright" in error_type or "Browser" in error_type:
            error_detail = f"Error en el navegador al procesar {url_str}: {error_msg}"
        elif "Connection" in error_type or "Network" in error_type or "Socket" in error_type:
            error_detail = f"Error de conexión al acceder a {url_str}: {error_msg}"
        elif "SSL" in error_type or "Certificate" in error_type:
            error_detail = f"Error de seguridad SSL al acceder a {url_str}: {error_msg}"
        else:
            error_detail = f"Error inesperado al procesar {url_str}: {error_type} - {error_msg}"
        
        # Registrar el error para depuración
        print(f"ERROR en /scrape: {error_detail}")
        
        # Devolver respuesta de error detallada
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/health")
def health_check():
    """Endpoint para verificar el estado de la API"""
    return {"status": "healthy", "message": "ScraperMaster API está funcionando correctamente"}

async def handle_cookie_dialogs(page):
    """Maneja diálogos comunes de consentimiento de cookies en varios sitios web."""
    try:
        # Botones de consentimiento en inglés principalmente (ya que ahora se configura el idioma en inglés)
        consent_buttons = [
            'I Accept',
            'Accept All',
            'Accept',
            'Agree to all',
            'Agree',
            'Continue',
            'OK',
            'Got it',
            'Allow',
            'Allow all',
            'Allow cookies',
            'Allow all cookies',
            'Yes',
            # Mantener algunos botones en otros idiomas por si acaso
            'Acepto',
            'Aceptar',
            'Alle akzeptieren'
        ]
        
        # Espera un breve momento para que los diálogos aparezcan
        await page.wait_for_timeout(1000)
        
        # Primero intenta con botones de consentimiento comunes
        for button in consent_buttons:
            try:
                # Intenta hacer clic en botones con texto exacto
                await page.click(f'text="{button}"', timeout=2000)
                print(f"Detectado y aceptado diálogo de cookies con botón '{button}'")
                await page.wait_for_timeout(2000)  # Espera para que el diálogo desaparezca
                return True
            except Exception:
                continue
                
        # Intenta selectores comunes para diálogos de cookies
        common_cookie_selectors = [
            'button#accept', 
            'button#acceptAll', 
            'button.accept-cookies',
            'button.accept-all-cookies',
            'button.cookie-accept',
            'button.cookie-accept-all',
            'button.js-accept-cookies',
            'button.js-accept-all-cookies',
            'button[data-testid="cookie-policy-dialog-accept-button"]',
            '#cookieConsentAcceptAll',
            '.cookie-banner__accept-all',
            '.cookie-consent__accept',
            '.cookie-accept-all-button',
            '#onetrust-accept-btn-handler',
            '.css-47sehv'  # Selector específico para YouTube
        ]
        
        for selector in common_cookie_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    await page.click(selector, timeout=2000)
                    print(f"Detectado y aceptado diálogo de cookies con selector '{selector}'")
                    await page.wait_for_timeout(2000)  # Espera para que el diálogo desaparezca
                    return True
            except Exception:
                continue
                
        # Intenta encontrar elementos iframe que puedan contener diálogos de cookies
        try:
            frames = page.frames
            for frame in frames:
                try:
                    # Intenta hacer clic en botones de aceptación dentro de iframes
                    for button in consent_buttons:
                        try:
                            if await frame.locator(f'text="{button}"').count() > 0:
                                await frame.click(f'text="{button}"', timeout=2000)
                                print(f"Detectado y aceptado diálogo de cookies en iframe con botón '{button}'")
                                await page.wait_for_timeout(2000)
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
            
        print("No se detectaron diálogos de cookies que requieran atención")
        return False
            
    except Exception as e:
        print(f"Error intentando manejar diálogos de cookies: {e}")
        return False
