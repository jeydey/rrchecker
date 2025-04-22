import requests
from bs4 import BeautifulSoup
import time
import logging
import random

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
CHECK_INTERVAL = 30
STOCK_NOTIFICATION_INTERVAL = 300
MAX_RETRIES = 3

# Configuración del nuevo proxy (ProxyLite)
PROXY_CONFIG = {
    'proxyUser': 'pl-decath940',
    'proxyPass': '110892',
    'proxyHost': 'gate-eu.proxylite.com',
    'proxyPort': '9595'
}
PROXY = f"http://{PROXY_CONFIG['proxyUser']}:{PROXY_CONFIG['proxyPass']}@{PROXY_CONFIG['proxyHost']}:{PROXY_CONFIG['proxyPort']}"
PROXIES = {"http": PROXY, "https": PROXY}

# User agents para rotar
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("✅ Notificación enviada a Telegram.")
        else:
            logging.error(f"❌ Error al enviar la notificación a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"❌ Excepción al enviar notificación Telegram: {e}")

def check_stock():
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Chromium";v="120", "Not=A?Brand";v="8"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "TE": "trailers"
    }

    cookies = {
        "CONSENT": "YES+cb.20210328-17-p0.es+FX+944",  # Simula consentimiento de cookies
    }

    try:
        logging.info(f"🔍 Verificando stock con proxy: {PROXY}")
        response = requests.get(PRODUCT_URL, headers=headers, cookies=cookies, proxies=PROXIES, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")
        if not size_selector:
            message = "⚠️ No se encontró el selector de tallas en la página."
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
            message = "❌ Sin stock por el momento."
            logging.info(message)
            return False

    except requests.exceptions.RequestException as e:
        message = f"❌ Error al verificar stock: {e}"
        logging.error(message)
        send_telegram_notification(message)
        return False

def main():
    send_telegram_notification("✅ Script activo. Verificando stock cada 30 segundos.")
    last_out_of_stock_notification_time = 0

    while True:
        if check_stock():
            last_out_of_stock_notification_time = 0
        else:
            current_time = time.time()
            if current_time - last_out_of_stock_notification_time >= STOCK_NOTIFICATION_INTERVAL:
                send_telegram_notification("📢 Seguimos sin stock. Continuamos monitoreando...")
                last_out_of_stock_notification_time = current_time

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
