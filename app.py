import requests
from bs4 import BeautifulSoup
import time
import logging
import random

# Configuración de producto y notificaciones
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
CHECK_INTERVAL = 30
STOCK_NOTIFICATION_INTERVAL = 300

# Configuración de ProxyLite
PROXY_CONFIG = {
    'proxyUser': 'pl-decath940',
    'proxyPass': '110892',
    'proxyHost': 'gate-eu.proxylite.com',
    'proxyPort': '9595'
}
PROXY = f"http://{PROXY_CONFIG['proxyUser']}:{PROXY_CONFIG['proxyPass']}@{PROXY_CONFIG['proxyHost']}:{PROXY_CONFIG['proxyPort']}"
PROXIES = {"http": PROXY, "https": PROXY}

# Lista de User Agents para rotar
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Safari/537.36"
]

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("✅ Notificación enviada.")
        else:
            logging.error(f"⚠️ Error enviando a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"❌ Excepción enviando notificación: {e}")

def check_stock():
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        logging.info("🌐 Realizando solicitud a la página del producto...")
        response = requests.get(PRODUCT_URL, headers=headers, proxies=PROXIES, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")
        if not size_selector:
            msg = "⚠️ No se encontró el selector de tallas."
            logging.warning(msg)
            send_telegram_notification(msg)
            return False

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
            msg = "❌ Aún sin stock."
            logging.info(msg)
            return False

    except requests.exceptions.HTTPError as e:
        msg = f"❌ Error HTTP: {e}"
        logging.error(msg)
        if e.response.status_code == 403:
            msg += "\n🚫 Posible bloqueo por Decathlon. Probando con otro User-Agent..."
        send_telegram_notification(msg)
        return False
    except Exception as e:
        msg = f"❌ Error general al verificar stock: {e}"
        logging.error(msg)
        send_telegram_notification(msg)
        return False

def main():
    send_telegram_notification("✅ Script iniciado y monitoreando stock.")

    last_notification_time = 0

    while True:
        if check_stock():
            last_notification_time = 0
        else:
            now = time.time()
            if now - last_notification_time > STOCK_NOTIFICATION_INTERVAL:
                send_telegram_notification("🕵️ Seguimos monitoreando. Sin stock por ahora.")
                last_notification_time = now

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
