import requests
from bs4 import BeautifulSoup
import time
import logging

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"

CHECK_INTERVAL = 300
STOCK_NOTIFICATION_INTERVAL = 300

# Credenciales GeoNode
GEONODE_USERNAME = "geonode_IDgCnOwpKG-type-residential"
GEONODE_PASSWORD = "ab0b0953-d053-4a24-835e-1e5feb82a217"
GEONODE_API_URL = "https://proxylist.geonode.com/api/proxy-list?limit=1&page=1&sort_by=lastChecked&sort_type=desc&protocols=http"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Error al enviar notificación: {e}")

def get_proxy_from_geonode():
    try:
        response = requests.get(GEONODE_API_URL, timeout=10)
        data = response.json()
        proxy_data = data["data"][0]
        ip = proxy_data["ip"]
        port = proxy_data["port"]
        proxy_url = f"http://{GEONODE_USERNAME}:{GEONODE_PASSWORD}@{ip}:{port}"
        return proxy_url
    except Exception as e:
        logging.error(f"Error al obtener proxy de GeoNode: {e}")
        return None

def test_proxy(proxy_url):
    try:
        test_url = "http://ip-api.com/json"
        response = requests.get(test_url, proxies={"http": proxy_url, "https": proxy_url}, timeout=15)
        if response.status_code == 200:
            info = response.json()
            ip = info.get("query", "Desconocido")
            country = info.get("country", "Desconocido")
            send_telegram_notification(f"✅ Proxy OK: IP={ip}, País={country}")
            return True
    except Exception as e:
        send_telegram_notification(f"❌ Proxy no válido: {proxy_url}\nError: {e}")
    return False

def check_stock(proxy_url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html",
        "Referer": "https://www.decathlon.es/",
    }
    try:
        response = requests.get(PRODUCT_URL, headers=headers, proxies={"http": proxy_url, "https": proxy_url}, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            send_telegram_notification("⚠️ No se encontró el selector de tallas.")
            return False

        in_stock = any("sku-selector__stock--inStock" in str(item)
                       for item in size_selector.find_all("li", class_="vtmn-sku-selector__item"))

        if in_stock:
            send_telegram_notification("🎉 ¡Producto disponible!")
            return True
        return False

    except Exception as e:
        send_telegram_notification(f"❌ Error al verificar stock: {e}")
        return False

def main():
    send_telegram_notification("✅ Script operativo con proxies dinámicos de GeoNode.")
    last_out_of_stock_notification_time = 0

    while True:
        proxy_url = get_proxy_from_geonode()
        if proxy_url and test_proxy(proxy_url):
            if check_stock(proxy_url):
                last_out_of_stock_notification_time = 0
            else:
                current_time = time.time()
                if current_time - last_out_of_stock_notification_time >= STOCK_NOTIFICATION_INTERVAL:
                    send_telegram_notification("⚠️ Aún sin stock.")
                    last_out_of_stock_notification_time = current_time
        else:
            send_telegram_notification("❌ No se pudo obtener o validar un proxy. Reintentando...")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
