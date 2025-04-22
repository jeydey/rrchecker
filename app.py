import requests
from bs4 import BeautifulSoup
import logging
import random
import time

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
CHECK_INTERVAL = 30  # Intervalo de verificación en segundos
STOCK_NOTIFICATION_INTERVAL = 300  # Intervalo mínimo entre notificaciones de "sin stock"
MAX_RETRIES = 3  # Máximo de reintentos

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_notification(message):
    """Envía un mensaje a Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("Notificación enviada a Telegram.")
        else:
            logging.error(f"Error al enviar la notificación a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Error al enviar la notificación a Telegram: {e}")

def fetch_page_using_scrapeops():
    """Obtiene la página de producto usando ScrapeOps."""
    scrapeops_api_key = "24f71537-bc7e-4c74-a75b-76e910aa1ab5"
    try:
        response = requests.get(
            url='https://proxy.scrapeops.io/v1/',
            params={
                'api_key': scrapeops_api_key,
                'url': PRODUCT_URL,
                'render_js': 'true',  # Habilitar ejecución de JavaScript
                'residential': 'true',  # Usar proxies residenciales
                'country': 'us',  # Proxies desde EE.UU.
            },
        )
        response.raise_for_status()  # Verifica si hubo un error en la solicitud
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al obtener la página usando ScrapeOps: {e}")
        send_telegram_notification(f"❌ Error al obtener la página usando ScrapeOps: {e}")
        return None

def check_stock():
    """Verifica el stock de un producto usando ScrapeOps."""
    logging.info("🔄 Verificando stock...")
    page_content = fetch_page_using_scrapeops()

    if page_content:
        soup = BeautifulSoup(page_content, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")
        
        if not size_selector:
            message = "⚠️ No se encontró el selector de tallas."
            logging.warning(message)
            send_telegram_notification(message)
            return False
        
        # Verifica si hay algún tamaño en stock
        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            message = "🎉 ¡Producto disponible!"
            logging.info(message)
            send_telegram_notification(message)
            return True
        else:
            message = "❌ Sin stock"
            logging.info(message)
            send_telegram_notification(message)
            return False
    return False

def main():
    send_telegram_notification("✅ El script está operativo y verificando stock cada 30 segundos.")
    
    while True:
        if check_stock():
            logging.info("¡Producto disponible!")
        else:
            current_time = time.time()
            logging.info("Producto no disponible, verificando nuevamente.")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()