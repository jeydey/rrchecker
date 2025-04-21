import requests
from bs4 import BeautifulSoup
import time
import logging
import base64

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
GEONODE_USERNAME = "geonode_IDgCnOwpKG-type-residential-country-es"  # Tu nombre de usuario de GeoNode
GEONODE_PASSWORD = "ab0b0953-d053-4a24-835e-1e5feb82a217"  # Tu contraseña de GeoNode
GEONODE_API_URL = "https://api.geonode.com/v1/proxies"  # URL de la API de GeoNode
CHECK_INTERVAL = 300  # Intervalo de verificación en segundos (5 minutos)
STOCK_NOTIFICATION_INTERVAL = 300  # Intervalo mínimo entre notificaciones de "sin stock"

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
            logging.error(f"Error al enviar la notificación a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Error al enviar la notificación a Telegram: {e}")

def fetch_proxies():
    """Obtiene una lista de proxies desde GeoNode usando Basic Authentication."""
    try:
        # Codificar las credenciales en Base64
        credentials = f"{GEONODE_USERNAME}:{GEONODE_PASSWORD}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        params = {
            "limit": 10,  # Número máximo de proxies a recuperar
            "sort_by": "last_checked",
            "sort_order": "asc"
        }
        response = requests.get(GEONODE_API_URL, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            proxies = [
                f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
                for proxy in data.get("data", [])
            ]
            logging.info(f"🔍 Obtenidos {len(proxies)} proxies desde GeoNode.")
            return proxies
        else:
            logging.error(f"❌ Error al obtener proxies desde GeoNode: {response.text}")
            return []
    except Exception as e:
        logging.error(f"❌ Error al obtener proxies desde GeoNode: {str(e)}")
        return []

def test_proxy(proxy):
    """Verifica si un proxy funciona realizando una solicitud de prueba."""
    try:
        test_url = "http://ip-api.com/json"
        response = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=5)
        if response.status_code == 200:
            ip_info = response.json()
            ip_address = ip_info.get("query", "Desconocido")
            country = ip_info.get("country", "Desconocido")
            message = f"✅ Proxy funcional: IP={ip_address}, País={country}"
            logging.info(message)
            send_telegram_notification(message)
            return True
    except Exception as e:
        message = f"❌ Proxy fallido: {proxy}. Error: {str(e)}"
        logging.error(message)
        send_telegram_notification(message)
    return False

def check_stock(proxy):
    """Verifica el stock del producto utilizando un proxy específico."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.5",
        "Referer": "https://www.decathlon.es/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        logging.info(f"🔄 Verificando stock con proxy: {proxy}")
        response = requests.get(PRODUCT_URL, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)
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
            send_telegram_notification(message)
            return False

    except requests.exceptions.RequestException as e:
        message = f"❌ Error al verificar el stock (Proxy: {proxy}): {str(e)}"
        logging.error(message)
        send_telegram_notification(message)
        return False

def main():
    send_telegram_notification("✅ El script está operativo y verificando stock cada 5 minutos.")

    while True:
        # Obtener una lista de proxies desde GeoNode
        proxies = fetch_proxies()
        if not proxies:
            send_telegram_notification("❌ No se pudieron cargar proxies. Intentando nuevamente en 5 minutos...")
            time.sleep(CHECK_INTERVAL)
            continue

        # Probar proxies hasta encontrar uno funcional
        working_proxy = None
        for proxy in proxies:
            if test_proxy(proxy):
                working_proxy = proxy
                break

        if not working_proxy:
            send_telegram_notification("❌ No se encontraron proxies funcionales. Intentando nuevamente en 5 minutos...")
            time.sleep(CHECK_INTERVAL)
            continue

        send_telegram_notification(f"✅ Proxy funcional encontrado: {working_proxy}")

        last_out_of_stock_notification_time = 0

        # Verificar el stock con el proxy funcional
        if check_stock(working_proxy):
            logging.info("¡Producto disponible!")
            last_out_of_stock_notification_time = 0
        else:
            current_time = time.time()
            if current_time - last_out_of_stock_notification_time >= STOCK_NOTIFICATION_INTERVAL:
                send_telegram_notification("⚠️ Aún no hay stock del producto. Seguimos verificando...")
                last_out_of_stock_notification_time = current_time

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()