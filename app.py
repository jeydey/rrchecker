import requests
from bs4 import BeautifulSoup
import time
import logging

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"

# Credenciales de GeoNode
GEONODE_USERNAME = "geonode_IDgCnOwpKG-type-residential"
GEONODE_PASSWORD = "ab0b0953-d053-4a24-835e-1e5feb82a217"
GEONODE_DNS = "92.204.164.15:9000"  # Dirección del servidor proxy de GeoNode

CHECK_INTERVAL = 300  # 5 minutos
STOCK_NOTIFICATION_INTERVAL = 300  # Mínimo 5 minutos entre mensajes de "sin stock"

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram_notification(message):
    """Envía un mensaje a Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("Notificación enviada a Telegram.")
        else:
            logging.error(f"Error al enviar notificación a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Error en la notificación a Telegram: {e}")

def test_proxy(proxy):
    """Verifica si el proxy funciona haciendo una solicitud de prueba."""
    try:
        test_url = "http://ip-api.com/json"
        response = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=15)
        if response.status_code == 200:
            ip_info = response.json()
            ip_address = ip_info.get("query", "Desconocido")
            country = ip_info.get("country", "Desconocido")
            message = f"✅ Proxy funcional: IP={ip_address}, País={country}"
            logging.info(message)
            send_telegram_notification(message)
            return True
    except Exception as e:
        message = f"❌ Proxy no válido: {proxy}. Error: {str(e)}"
        logging.error(message)
        send_telegram_notification(message)
    return False

def check_stock(proxy):
    """Verifica el stock del producto usando el proxy."""
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
        logging.info(f"🔄 Verificando stock con proxy: {proxy}")
        response = requests.get(PRODUCT_URL, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            message = f"⚠️ No se encontró el selector de tallas (Proxy: {proxy})"
            logging.warning(message)
            send_telegram_notification(message)
            return False

        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            message = f"🎉 ¡Producto disponible! (Proxy: {proxy})"
            logging.info(message)
            send_telegram_notification(message)
            return True
        else:
            message = f"❌ Sin stock (Proxy: {proxy})"
            logging.info(message)
            return False

    except requests.exceptions.RequestException as e:
        message = f"❌ Error al verificar stock (Proxy: {proxy}): {str(e)}"
        logging.error(message)
        send_telegram_notification(message)
        return False

def main():
    send_telegram_notification("✅ Script operativo. Verificando stock cada 5 minutos...")

    # Configurar el proxy
    proxy = f"http://{GEONODE_USERNAME}:{GEONODE_PASSWORD}@{GEONODE_DNS}"

    if not test_proxy(proxy):
        send_telegram_notification("❌ El proxy no funciona. Intentando nuevamente en 5 minutos...")
        return

    last_out_of_stock_notification_time = 0

    while True:
        if check_stock(proxy):
            logging.info("✅ Producto disponible.")
            last_out_of_stock_notification_time = 0
        else:
            current_time = time.time()
            if current_time - last_out_of_stock_notification_time >= STOCK_NOTIFICATION_INTERVAL:
                send_telegram_notification("⚠️ Aún no hay stock. Seguimos verificando...")
                last_out_of_stock_notification_time = current_time

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
