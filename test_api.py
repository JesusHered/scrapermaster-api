"""
Ejemplo de uso del endpoint de scraping
"""
import requests
import json

# URL base de la API
BASE_URL = "http://localhost:8000"

def test_scraping_endpoint():
    """Prueba el endpoint de scraping"""
    
    # URL de ejemplo para probar
    test_url = "https://example.com"
    
    # Datos a enviar
    payload = {
        "url": test_url
    }
    
    try:
        # Realizar petición POST
        response = requests.post(f"{BASE_URL}/scrape", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Scraping exitoso!")
            print(f"📖 Título: {result['title']}")
            print(f"🔗 URL: {result['url']}")
            print(f"📊 Metadata: {json.dumps(result['metadata'], indent=2)}")
            print(f"🖼️ Imágenes encontradas: {len(result['images'])}")
            print(f"🔗 Enlaces encontrados: {len(result['links'])}")
            print(f"💰 Montos detectados: {len(result['amounts'])}")
            
            print("\n📝 Contenido en Markdown (primeros 500 caracteres):")
            print(result['markdown_content'][:500] + "...")
            
            if result['amounts']:
                print(f"\n💰 Montos encontrados: {result['amounts'][:5]}")
            
            if result['structured_data']['tables']:
                print(f"\n📊 Tablas encontradas: {len(result['structured_data']['tables'])}")
            
            if result['structured_data']['lists']:
                print(f"\n📋 Listas encontradas: {len(result['structured_data']['lists'])}")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")

def test_health_endpoint():
    """Prueba el endpoint de health check"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API funcionando correctamente")
            print(response.json())
        else:
            print(f"❌ Error en health check: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    print("🚀 Probando ScraperMaster API")
    print("=" * 50)
    
    # Probar health check
    print("\n1. Probando health check...")
    test_health_endpoint()
    
    # Probar scraping
    print("\n2. Probando endpoint de scraping...")
    test_scraping_endpoint()
