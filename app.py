import requests
from bs4 import BeautifulSoup
import time
import logging

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"

CHECK_INTERVAL = 300  # 5 minutos
STOCK_NOTIFICATION_INTERVAL = 300

# Proxy dinámico de GeoNode
GEONODE_PROXIES = [
    {
        "username": "geonode_IDgCnOwpKG-type-residential",
        "password": "ab0b0953-d053-4a24-835e-1e5feb82a217",
        "dns": "premium.residential.geonode.com:9000"
    }
]

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("Notificación enviada a Telegram.")
        else:
            logging.error(f"Error al enviar notificación: {response.text}")
    except Exception as e:
        logging.error(f"Error al enviar notificación: {e}")

def build_proxy_url(proxy_data):
    return f"http://{proxy_data['username']}:{proxy_data['password']}@{proxy_data['dns']}"

def test_proxy(proxy_url):
    try:
        test_url = "http://ip-api.com/json"
        response = requests.get(test_url, proxies={"http": proxy_url, "https": proxy_url}, timeout=15)
        if response.status_code == 200:
            ip_info = response.json()
            ip_address = ip_info.get("query", "Desconocido")
            country = ip_info.get("country", "Desconocido")
            message = f"✅ Proxy funcional: IP={ip_address}, País={country}"
            logging.info(message)
            send_telegram_notification(message)
            return True
    except Exception as e:
        message = f"❌ Proxy no válido: {proxy_url}. Error: {str(e)}"
        logging.warning(message)
        send_telegram_notification(message)
    return False

def check_stock(proxy_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.5",
        "Referer": "https://www.decathlon.es/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        logging.info(f"🔄 Verificando stock con proxy: {proxy_url}")
        response = requests.get(PRODUCT_URL, headers=headers, proxies={"http": proxy_url, "https": proxy_url}, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            message = f"⚠️ No se encontró el selector de tallas (Proxy: {proxy_url})"
            logging.warning(message)
            send_telegram_notification(message)
            return False

        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            message = f"🎉 ¡Producto disponible! (Proxy: {proxy_url})"
            logging.info(message)
            send_telegram_notification(message)
            return True
        else:
            logging.info("❌ Sin stock.")
            return False

    except requests.exceptions.RequestException as e:
        message = f"❌ Error al verificar stock con proxy {proxy_url}: {e}"
        logging.warning(message)
        send_telegram_notification(message)
        return False

def main():
    send_telegram_notification("✅ Script operativo. Verificando stock cada 5 minutos...")

    last_out_of_stock_notification_time = 0

    while True:
        proxy_found = False
        for proxy_data in GEONODE_PROXIES:
            proxy_url = build_proxy_url(proxy_data)

            if test_proxy(proxy_url):
                proxy_found = True
                if check_stock(proxy_url):
                    last_out_of_stock_notification_time = 0
                else:
                    current_time = time.time()
                    if current_time - last_out_of_stock_notification_time >= STOCK_NOTIFICATION_INTERVAL:
                        send_telegram_notification("⚠️ Aún no hay stock. Seguimos verificando...")
                        last_out_of_stock_notification_time = current_time
                break  # Si un proxy funcionó, no sigue probando los demás

        if not proxy_found:
            send_telegram_notification("❌ No hay proxies funcionales. Reintentando en 5 minutos...")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
