import requests
from bs4 import BeautifulSoup
import logging
import random
import time
from datetime import datetime, timedelta
import pytz

# Configuración
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
SCRAPEOPS_API_KEYS = [
    "98771a3f-7adf-4924-b244-40760e65ea02",
    "bb8e9114-f295-42cb-ae54-71b59305f97d"
]

# Tiempos base
STOCK_CHECK_INTERVAL_NORMAL = 600  # 10 minutos
STOCK_CHECK_INTERVAL_HIGH = 300    # 5 minutos
SUMMARY_INTERVAL = 1800  # 30 minutos

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Almacenar comprobaciones
stock_checks = []
last_summary_time = time.time()
check_count = 0

# Zona horaria Madrid
madrid_tz = pytz.timezone("Europe/Madrid")


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
                'api_key': SCRAPEOPS_API_KEYS[0],  # Solo necesitamos headers aquí
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
    global check_count
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
            return (timestamp, "⚠️ Error al analizar HTML", api_used)

        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            msg = f"🎉 ¡[{timestamp}] Producto disponible! (API: {api_used})"
            logging.info(msg)
            send_telegram_notification(msg)
            return (timestamp, "✅ CON STOCK", api_used)
        else:
            logging.info(f"❌ [{timestamp}] Producto sin stock. (API: {api_used})")
            return (timestamp, "❌ Sin stock", api_used)

    return (timestamp, "⚠️ Error al obtener página", api_used)


def send_summary():
    if not stock_checks:
        return
    summary_lines = ["📝 *Resumen de comprobaciones* (últimos 30 min):"]
    for time_checked, result, api in stock_checks:
        summary_lines.append(f"- {time_checked}: {result} (API: {api})")

    summary_message = "\n".join(summary_lines)
    send_telegram_notification(summary_message)
    stock_checks.clear()


def main():
    global last_summary_time
    send_telegram_notification("✅ El script ha iniciado correctamente.")
    
    vigilant_mode = False
    vigilant_check_done = False

    while True:
        now = datetime.now(madrid_tz)
        today = now.date()
        is_april_24 = today == datetime(2025, 4, 24, tzinfo=madrid_tz).date()

        # Activar vigilancia especial a partir del 24 a las 00:00 (hora Madrid)
        if is_april_24 and now.hour == 0 and now.minute == 0 and not vigilant_check_done:
            send_telegram_notification("📆 Es 24 de abril en Madrid.\n✅ Se ha hecho una comprobación inmediata.\n⏱️ Se activa vigilancia intensiva (cada 5 minutos).")
            check_result = check_stock()
            if check_result:
                stock_checks.append(check_result)
            vigilant_mode = True
            vigilant_check_done = True

        interval = STOCK_CHECK_INTERVAL_HIGH if vigilant_mode else STOCK_CHECK_INTERVAL_NORMAL

        check_result = check_stock()
        if check_result:
            stock_checks.append(check_result)

        now_unix = time.time()
        if now_unix - last_summary_time >= SUMMARY_INTERVAL:
            send_summary()
            last_summary_time = now_unix

        time.sleep(interval)


if __name__ == "__main__":
    main()
