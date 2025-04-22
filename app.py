import requests
from bs4 import BeautifulSoup
import logging
import random
import time
from datetime import datetime

# Configuración
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
STOCK_CHECK_INTERVAL = 600  # 10 minutos
SUMMARY_INTERVAL = 1800  # 30 minutos

SCRAPEOPS_API_KEY = "024be52e-c49b-4885-9320-1a9b0f14bf10"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Almacenar comprobaciones
stock_checks = []
last_summary_time = time.time()

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
    except Exception as e:
        logging.error(f"Error al obtener headers de ScrapeOps: {e}")
    
    return {"User-Agent": "Mozilla/5.0"}  # Fallback

def fetch_page_using_scrapeops():
    headers = get_random_headers()
    retries = 3  # Intentar hasta 3 veces
    for attempt in range(retries):
        try:
            response = requests.get(
                url='https://proxy.scrapeops.io/v1/',
                params={
                    'api_key': SCRAPEOPS_API_KEY,
                    'url': PRODUCT_URL,
                    'render_js': 'true',
                    'residential': 'true',
                    'country': 'es',
                },
                headers=headers,
                timeout=40  # Timeout aumentado a 40 segundos
            )
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener página usando ScrapeOps (Intento {attempt + 1}): {e}")
            if attempt < retries - 1:
                logging.info("Reintentando en 5 segundos...")
                time.sleep(5)  # Esperar 5 segundos antes de reintentar
            else:
                logging.error("Se alcanzó el máximo de intentos. No se pudo obtener la página.")
                return None

def check_stock():
    logging.info("🔍 Verificando stock...")
    page_content = fetch_page_using_scrapeops()
    timestamp = datetime.now().strftime("%H:%M:%S")

    if page_content:
        soup = BeautifulSoup(page_content, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            msg = f"⚠️ [{timestamp}] No se encontró el selector de tallas."
            logging.warning(msg)
            return (timestamp, "⚠️ Error al analizar HTML")
        
        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            msg = f"🎉 ¡[{timestamp}] Producto disponible!"
            logging.info(msg)
            send_telegram_notification(msg)
            return (timestamp, "✅ CON STOCK")
        else:
            logging.info(f"❌ [{timestamp}] Producto sin stock.")
            return (timestamp, "❌ Sin stock")

    return (timestamp, "⚠️ Error al obtener página")

def send_summary():
    if not stock_checks:
        return
    summary_lines = ["📝 *Resumen de comprobaciones* (últimos 30 min):"]
    for time_checked, result in stock_checks:
        summary_lines.append(f"- {time_checked}: {result}")
    
    summary_message = "\n".join(summary_lines)
    send_telegram_notification(summary_message)
    stock_checks.clear()

def main():
    global last_summary_time
    send_telegram_notification("✅ El script ha iniciado correctamente.")
    
    while True:
        check_result = check_stock()
        if check_result:
            stock_checks.append(check_result)

        now = time.time()
        if now - last_summary_time >= SUMMARY_INTERVAL:
            send_summary()
            last_summary_time = now

        time.sleep(STOCK_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
