import requests
from bs4 import BeautifulSoup
import time
import logging
import random

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
GEONODE_USERNAME = "geonode_IDgCnOwpKG-type-residential"
GEONODE_PASSWORD = "ab0b0953-d053-4a24-835e-1e5feb82a217"
GEONODE_ENDPOINT = "proxy.geonode.io:9000"
CHECK_INTERVAL = 30  # Intervalo de verificación en segundos
STOCK_NOTIFICATION_INTERVAL = 300  # Intervalo mínimo entre notificaciones de "sin stock"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.106 Safari/537.36 Edg/123.0.2420.81"
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.5",
        "Referer": "https://www.decathlon.es/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def send_telegram_notification(message):
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

def test_proxy(proxy):
    try:
        test_url = "http://ip-api.com/json"
        response = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=10)
        if response.status_code == 200:
            ip_info = response.json()
            ip_address = ip_info.get("query", "Desconocido")
            country = ip_info.get("country", "Desconocido")
            message = f"✅ Proxy funcional: IP={ip_address}, País={country}"
            logging.info(message)
            send_telegram_notification(f"> DecathCHK:\n{message}")
            return True
    except Exception as e:
        message = f"❌ Proxy fallido: {proxy}. Error: {str(e)}"
        logging.error(message)
        send_telegram_notification(f"> DecathCHK:\n{message}")
    return False

def fetch_proxies():
    try:
        proxy = f"http://{GEONODE_USERNAME}:{GEONODE_PASSWORD}@{GEONODE_ENDPOINT}"
        logging.info("🔍 Obteniendo proxy desde Geonode...")
        return [proxy]
    except Exception as e:
        message = f"❌ Error al obtener proxies desde Geonode: {str(e)}"
        logging.error(message)
        send_telegram_notification(f"> DecathCHK:\n{message}")
        return []

def check_stock(proxies):
    for proxy in proxies:
        try:
            headers = get_random_headers()
            logging.info(f"🔄 Verificando stock con proxy: {proxy}")
            response = requests.get(PRODUCT_URL, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            size_selector = soup.find("ul", class_="vtmn-sku-selector__items")
            if not size_selector:
                message = f"⚠️ No se encontró el selector de tallas (Proxy: {proxy})"
                logging.warning(message)
                send_telegram_notification(f"> DecathCHK:\n{message}")
                continue

            in_stock = any(
                "sku-selector__stock--inStock" in str(item)
                for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
            )

            if in_stock:
                message = f"🎉 ¡Producto disponible! (Proxy: {proxy})"
                logging.info(message)
                send_telegram_notification(f"> DecathCHK:\n{message}")
                return True
            else:
                message = f"❌ Sin stock (Proxy: {proxy})"
                logging.info(message)
                send_telegram_notification(f"> DecathCHK:\n{message}")

        except requests.exceptions.RequestException as e:
            message = f"❌ Error al verificar el stock (Proxy: {proxy}): {str(e)}"
            logging.error(message)
            send_telegram_notification(f"> DecathCHK:\n{message}")
            continue

    message = "❌ Todos los proxies fallaron."
    logging.error(message)
    send_telegram_notification(f"> DecathCHK:\n{message}")
    return False

def main():
    send_telegram_notification("> DecathCHK:\n✅ El script está operativo y verificando stock cada 30 segundos.")

    last_out_of_stock_notification_time = 0

    while True:
        proxies = fetch_proxies()
        working_proxies = [proxy for proxy in proxies if test_proxy(proxy)]

        if working_proxies:
            send_telegram_notification(f"> DecathCHK:\n✅ Proxies funcionales encontrados: {len(working_proxies)}")
            if check_stock(working_proxies):
                last_out_of_stock_notification_time = 0
            else:
                current_time = time.time()
                if current_time - last_out_of_stock_notification_time >= STOCK_NOTIFICATION_INTERVAL:
                    send_telegram_notification("> DecathCHK:\n⚠️ Aún no hay stock del producto. Seguimos verificando...")
                    last_out_of_stock_notification_time = current_time
        else:
            send_telegram_notification("> DecathCHK:\n❌ No se encontraron proxies funcionales. Intentando nuevamente...")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
