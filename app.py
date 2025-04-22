import requests
from bs4 import BeautifulSoup
import time
import logging

# Configuración de producto
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-cross-country-race-700-gris-cuadro-aluminio/_/R-p-337291"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"

# Configuración de ScrapeOps
SCRAPEOPS_API_KEY = '24f71537-bc7e-4c74-a75b-76e910aa1ab5'

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# User Agents para rotar
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

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

def check_stock():
    """Verifica el stock del producto usando ScrapeOps."""
    try:
        response = requests.get(
            url='https://proxy.scrapeops.io/v1/',
            params={
                'api_key': SCRAPEOPS_API_KEY,
                'url': PRODUCT_URL,
                'render_js': 'true',
                'residential': 'true',
                'country': 'us',
            }
        )

        if response.status_code == 200:
            logging.info("Solicitud exitosa, procesando datos...")
            soup = BeautifulSoup(response.content, "html.parser")
            size_selector = soup.find("ul", class_="vtmn-sku-selector__items")
            if not size_selector:
                message = f"⚠️ No se encontró el selector de tallas para el producto."
                logging.warning(message)
                send_telegram_notification(message)
                return False

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
        else:
            logging.error(f"Error al obtener la página: {response.status_code}")
            send_telegram_notification(f"❌ Error al obtener la página: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"Error en la solicitud: {e}")
        send_telegram_notification(f"❌ Error al verificar el stock: {e}")
        return False

def main():
    send_telegram_notification("✅ El script está operativo y verificando stock cada 30 segundos.")
    while True:
        logging.info("Verificando stock...")
        if check_stock():
            logging.info("¡Producto disponible!")
        else:
            logging.info("Producto no disponible. Seguimos verificando...")

        time.sleep(30)  # Intervalo de verificación

if __name__ == "__main__":
    main()
