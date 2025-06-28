from fastapi import HTTPException
from pydantic import HttpUrl
from markdownify import markdownify as md
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import re
import asyncio
from typing import Dict, List
from ..main import ScrapedContent, ContentProcessor, handle_cookie_dialogs

async def scrape_url_content(url: str) -> ScrapedContent:
    """Extrae contenido de una URL usando Playwright"""
    try:
        async with async_playwright() as p:
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
                locale='en-US',  # Establecer idioma como inglés americano
                timezone_id='America/New_York',  # Usar zona horaria estadounidense para coherencia
                accept_language='en-US,en;q=0.9'  # Preferir contenido en inglés
            )
            page = await context.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Intentar manejar diálogos de cookies comunes
            await handle_cookie_dialogs(page)
            
            # Aumentamos el tiempo de espera a 5 segundos para permitir que la página cargue completamente
            await page.wait_for_timeout(5000)
            title = await page.title()
            html_content = await page.content()
            images = await page.evaluate('''
                () => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs.map(img => {
                        const src = img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src');
                        return src;
                    }).filter(src => src && src.startsWith('http'));
                }
            ''')
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
            processor = ContentProcessor()
            clean_html = processor.clean_and_organize_content(html_content)
            markdown_content = md(clean_html, heading_style="ATX")
            soup = BeautifulSoup(html_content, 'html.parser')
            amounts = processor.extract_amounts(soup.get_text())
            structured_data = processor.extract_structured_data(soup)
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
                images=images[:20],
                links=links[:50],
                amounts=amounts,
                structured_data=structured_data
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la URL: {str(e)}")