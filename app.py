import requests
from bs4 import BeautifulSoup
import logging
import random
import time

# Configuración
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
CHECK_INTERVAL = 600  # Verificación de stock cada 10 minutos
HEARTBEAT_INTERVAL = 300  # Mensaje de estado cada 5 minutos
STOCK_NOTIFICATION_INTERVAL = 600  # Notificación "sin stock" cada 10 minutos

# ScrapeOps
SCRAPEOPS_API_KEY = "24f71537-bc7e-4c74-a75b-76e910aa1ab5"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Tiempos para control de notificaciones
last_heartbeat = 0
last_stock_notification = 0

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("📤 Notificación enviada a Telegram.")
        else:
            logging.error(f"Error al enviar notificación a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Excepción al enviar notificación a Telegram: {e}")

def get_random_headers():
    """Obtiene un header aleatorio de ScrapeOps."""
    try:
        response = requests.get(
            url='https://headers.scrapeops.io/v1/browser-headers',
            params={
                'api_key': SCRAPEOPS_API_KEY,
                'num_results': 5
            },
            timeout=10
        )
        response.raise_for_status()
        headers_list = response.json().get("result", [])
        if headers_list:
            return random.choice(headers_list)
        else:
            logging.warning("No se recibieron headers de ScrapeOps.")
    except Exception as e:
        logging.error(f"Error al obtener headers de ScrapeOps: {e}")
    
    return {"User-Agent": "Mozilla/5.0"}  # Fallback básico

def fetch_page_using_scrapeops():
    headers = get_random_headers()
    try:
        response = requests.get(
            url='https://proxy.scrapeops.io/v1/',
            params={
                'api_key': SCRAPEOPS_API_KEY,
                'url': PRODUCT_URL,
                'render_js': 'true',
                'residential': 'true',
                'country': 'us',
            },
            headers=headers,
            timeout=20
        )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al obtener página usando ScrapeOps: {e}")
        send_telegram_notification(f"❌ Error al obtener la página usando ScrapeOps: {e}")
        return None

def check_stock():
    logging.info("🔍 Verificando stock...")
    page_content = fetch_page_using_scrapeops()

    if page_content:
        soup = BeautifulSoup(page_content, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            msg = "⚠️ No se encontró el selector de tallas."
            logging.warning(msg)
            send_telegram_notification(msg)
            return None

        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            msg = "🎉 ¡Producto disponible!"
            logging.info(msg)
            send_telegram_notification(msg)
            return True
        else:
            logging.info("❌ Producto sin stock.")
            return False
    return None

def main():
    global last_heartbeat, last_stock_notification
    send_telegram_notification("✅ El script está operativo.")

    while True:
        now = time.time()

        # Mensaje de funcionamiento cada 5 min
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            send_telegram_notification("💤 Script funcionando. Sin novedades.")
            last_heartbeat = now

        # Comprobar stock
        result = check_stock()
        if result is True:
            last_stock_notification = now  # Si hay stock, reiniciamos contador
        elif result is False and now - last_stock_notification >= STOCK_NOTIFICATION_INTERVAL:
            send_telegram_notification("❌ Producto aún sin stock.")
            last_stock_notification = now

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
