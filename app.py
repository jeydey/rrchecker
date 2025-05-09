import requests
from bs4 import BeautifulSoup
import logging
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

# Configuración
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN_STOCK = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"  # Solo para alertas de stock
TELEGRAM_BOT_TOKEN_LOG = "7511516134:AAGtxLvOsmkiKMQZaSm8gCvgiG18G3LbUoY"  # Para logs de cada comprobación
TELEGRAM_CHAT_ID = "871212552"
SCRAPEOPS_API_KEYS = [
    "9ee3fbae-68a9-47bb-bace-b9554aa60283",
    "7428a0f4-045c-43f1-aa82-ae7645450a42",
    "5cedec06-1fa0-4e5c-bcef-86dcdde70215",
    "d71f6eaf-4334-4b0f-901d-e91f1ee1ae47",
    "8ea480b3-a876-4806-b7bb-8fc9a8cf617b",
    "d061d795-4922-4b04-ae38-be3928e7fe40",
    "ae5e53a2-899a-494d-9f2d-5f220366df63",
    "5becc9ae-66f1-456d-9bd1-ae8feda6fe27"
]

# Tiempos base
STOCK_CHECK_INTERVAL_NORMAL = 1800  # 30 minutos
STOCK_SUMMARY_INTERVAL = 3600  # 1 hora para resumen de stock

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Zona horaria Madrid
madrid_tz = ZoneInfo("Europe/Madrid")

check_count = 0
last_stock_status = None
last_summary_time = time.time()

def send_telegram_notification(message, stock_alert=False):
    try:
        token = TELEGRAM_BOT_TOKEN_STOCK if stock_alert else TELEGRAM_BOT_TOKEN_LOG
        prefix = "📦 STOCK |" if stock_alert else "📄 LOG |"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": f"{prefix} {message}"}
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
                'api_key': SCRAPEOPS_API_KEYS[0],
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
    return {"User-Agent": "Mozilla/5.0"}

def fetch_page_using_scrapeops():
    global check_count
    headers = get_random_headers()
    api_key = SCRAPEOPS_API_KEYS[check_count % len(SCRAPEOPS_API_KEYS)]

    for attempt in range(3):
        try:
            response = requests.get(
                url='https://proxy.scrapeops.io/v1/',
                params={
                    'api_key': api_key,
                    'url': PRODUCT_URL,
                    'render_js': 'true',
                    'residential': 'true',
                    'country': 'es',
                },
                headers=headers,
                timeout=20
            )
            response.raise_for_status()
            return response.content, api_key
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener página usando ScrapeOps (Intento {attempt + 1}): {e}")
            time.sleep(2)

    return None, api_key

def check_stock():
    global check_count, last_stock_status, last_summary_time
    logging.info("🔍 Verificando stock...")
    page_content, api_used = fetch_page_using_scrapeops()
    timestamp = datetime.now(madrid_tz).strftime("%H:%M:%S")
    check_count += 1

    if page_content:
        soup = BeautifulSoup(page_content, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            msg = f"⚠️ [{timestamp}] No se encontró el selector de tallas. (API: {api_used})"
            logging.warning(msg)
            return

        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            msg = f"🎉 ¡[{timestamp}] Producto disponible! (API: {api_used})"
            logging.info(msg)
            send_telegram_notification(msg, stock_alert=True)
            last_stock_status = True
        else:
            last_stock_status = False

    if time.time() - last_summary_time >= STOCK_SUMMARY_INTERVAL:
        summary_msg = f"⏱️ [{timestamp}] Estado actual: {'Disponible' if last_stock_status else 'Sin stock'} (API: {api_used})"
        send_telegram_notification(summary_msg, stock_alert=True)
        last_summary_time = time.time()

def main():
    send_telegram_notification("✅ El script ha iniciado correctamente.", stock_alert=True)

    while True:
        check_stock()
        time.sleep(STOCK_CHECK_INTERVAL_NORMAL)

if __name__ == "__main__":
    main()
