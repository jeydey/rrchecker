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

SCRAPEOPS_API_KEYS = [
    "b6d6356d-0391-4887-9e1d-01853b77eadc",
    "548a8a8b-65d0-4469-9bf6-c1e17382471b"
]
api_key_index = 0

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Almacenar comprobaciones
stock_checks = []
last_summary_time = time.time()


def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("📤 Notificación enviada a Telegram.")
        else:
            logging.error(f"Error al enviar notificación a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Excepción al enviar notificación a Telegram: {e}")


def get_random_headers(api_key):
    try:
        response = requests.get(
            url='https://headers.scrapeops.io/v1/browser-headers',
            params={
                'api_key': api_key,
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


def fetch_page_using_scrapeops(api_key):
    headers = get_random_headers(api_key)
    max_retries = 3
    for attempt in range(1, max_retries + 1):
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
            return response.content
        except requests.exceptions.HTTPError as e:
            logging.error(f"Error al obtener página usando ScrapeOps (Intento {attempt}): {e}")
            if response.status_code == 401:
                break  # No tiene sentido reintentar si no hay créditos
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al obtener página usando ScrapeOps (Intento {attempt}): {e}")
        time.sleep(2)
    return None


def check_stock():
    global api_key_index
    current_api_key = SCRAPEOPS_API_KEYS[api_key_index]
    api_key_index = (api_key_index + 1) % len(SCRAPEOPS_API_KEYS)

    logging.info("🔍 Verificando stock...")
    page_content = fetch_page_using_scrapeops(current_api_key)
    timestamp = datetime.now().strftime("%H:%M:%S")

    if page_content:
        soup = BeautifulSoup(page_content, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            msg = f"⚠️ [{timestamp}] No se encontró el selector de tallas."
            logging.warning(msg)
            return (timestamp, "⚠️ Error al analizar HTML", current_api_key)

        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            msg = f"🎉 ¡[{timestamp}] Producto disponible!"
            logging.info(msg)
            send_telegram_notification(msg)
            return (timestamp, "✅ CON STOCK", current_api_key)
        else:
            logging.info(f"❌ [{timestamp}] Producto sin stock.")
            return (timestamp, "❌ Sin stock", current_api_key)

    return (timestamp, "⚠️ Error al obtener página", current_api_key)


def send_summary():
    if not stock_checks:
        return
    summary_lines = ["📝 *Resumen de comprobaciones* (últimos 30 min):"]
    for time_checked, result, api_used in stock_checks:
        summary_lines.append(f"- {time_checked}: {result} (API usada: `{api_used[:8]}...`)")

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
