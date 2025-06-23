import requests
import json

# Ejemplo de uso del endpoint de screenshots
def test_screenshots_endpoint():
    """Prueba el endpoint de screenshots"""
    
    # URL del endpoint
    endpoint_url = "http://localhost:8000/screenshots"
    
    # Datos de la solicitud
    data = {
        "url": "https://example.com"
    }
    
    try:
        # Hacer la solicitud POST
        response = requests.post(endpoint_url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Screenshots capturadas exitosamente!")
            print(f"📊 Total de screenshots: {result['total_screenshots']}")
            print(f"🔗 URL procesada: {result['url']}")
            print("📸 Screenshots disponibles:")
            
            for screenshot_name, base64_data in result['screenshots'].items():
                print(f"  - {screenshot_name}: {len(base64_data)} caracteres en base64")
                
                # Opcional: guardar las imágenes localmente para verificar
                import base64
                with open(f"{screenshot_name}.png", "wb") as f:
                    f.write(base64.b64decode(base64_data))
                print(f"    💾 Guardado como {screenshot_name}.png")
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📝 Mensaje: {response.json()}")
            
    except Exception as e:
        print(f"💥 Error ejecutando la prueba: {e}")

if __name__ == "__main__":
    test_screenshots_endpoint()
