import requests
from bs4 import BeautifulSoup
import time

# Configuración de la URL del producto
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"

# Configuración de Geonode
GEONODE_USERNAME = "geonode_IDgCnOwpKG-type-residential-country-es"
GEONODE_PASSWORD = "ab0b0953-d053-4a24-835e-1e5feb82a217"
GEONODE_DNS = "92.204.164.15:9000"

def send_telegram_notification(message):
    """Envía un mensaje a Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Notificación enviada a Telegram.")
        else:
            print(f"Error al enviar la notificación a Telegram: {response.text}")
    except Exception as e:
        print(f"Error al enviar la notificación a Telegram: {e}")

def test_proxy(proxy):
    """Verifica si un proxy funciona realizando una solicitud de prueba."""
    try:
        test_url = "http://ip-api.com/json"  # URL para probar proxies
        response = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=5)
        if response.status_code == 200:
            ip_info = response.json()
            ip_address = ip_info.get("query", "Desconocido")
            country = ip_info.get("country", "Desconocido")
            notification = f"✅ Proxy funcional: IP={ip_address}, País={country}"
            send_telegram_notification(notification)
            return True
    except Exception as e:
        notification = f"❌ Proxy fallido: {proxy}. Error: {str(e)}"
        send_telegram_notification(notification)
    return False

def fetch_proxies():
    """Obtiene proxies desde Geonode."""
    try:
        proxy = f"http://{GEONODE_USERNAME}:{GEONODE_PASSWORD}@{GEONODE_DNS}"
        notification = f"🔍 Obteniendo proxy desde Geonode..."
        send_telegram_notification(notification)
        return [proxy]  # Devuelve el proxy configurado
    except Exception as e:
        notification = f"❌ Error al obtener proxies desde Geonode: {str(e)}"
        send_telegram_notification(notification)
        return []

def check_stock(proxies):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.5",
        "Referer": "https://www.decathlon.es/",
        "DNT": "1",  # Do Not Track
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    for proxy in proxies:
        try:
            notification = f"🔄 Verificando stock con proxy: {proxy}"
            send_telegram_notification(notification)

            # Realizar la solicitud HTTP a la página del producto
            response = requests.get(PRODUCT_URL, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)
            response.raise_for_status()

            # Analizar el HTML con BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Buscar el selector de tallas
            size_selector = soup.find("ul", class_="vtmn-sku-selector__items")
            if not size_selector:
                notification = f"⚠️ No se encontró el selector de tallas (Proxy: {proxy})"
                send_telegram_notification(notification)
                continue

            # Verificar si alguna talla tiene stock
            in_stock = any(
                "sku-selector__stock--inStock" in str(item)
                for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
            )

            if in_stock:
                notification = f"🎉 ¡Producto disponible! (Proxy: {proxy})"
                send_telegram_notification(notification)
                return True
            else:
                notification = f"❌ Sin stock (Proxy: {proxy})"
                send_telegram_notification(notification)

        except Exception as e:
            notification = f"❌ Error al verificar el stock (Proxy: {proxy}): {str(e)}"
            send_telegram_notification(notification)
            continue

    notification = "❌ Todos los proxies fallaron."
    send_telegram_notification(notification)
    return False

def main():
    # Enviar mensaje de inicio INMEDIATAMENTE
    send_telegram_notification("✅ El script está operativo y verificando stock cada 5 minutos.")

    # Cargar proxies desde Geonode
    proxies = fetch_proxies()
    if not proxies:
        send_telegram_notification("❌ No se pudieron cargar proxies. Intentando nuevamente en 5 minutos...")
        return

    # Filtrar proxies funcionales
    working_proxies = []
    for proxy in proxies:
        if test_proxy(proxy):
            working_proxies.append(proxy)

    if not working_proxies:
        send_telegram_notification("❌ No se encontraron proxies funcionales. Intentando nuevamente en 5 minutos...")
        return

    send_telegram_notification(f"✅ Proxies funcionales encontrados: {len(working_proxies)}")

    # Variables para controlar el tiempo entre mensajes de "sin stock"
    last_out_of_stock_notification_time = 0
    out_of_stock_interval = 300  # Intervalo de 5 minutos en segundos

    while True:
        print("Verificando stock...")
        if check_stock(working_proxies):
            print("¡Producto disponible!")
            last_out_of_stock_notification_time = 0  # Reiniciar el contador
        else:
            print("Sin stock.")
            current_time = time.time()
            # Verificar si han pasado 5 minutos desde la última notificación de "sin stock"
            if current_time - last_out_of_stock_notification_time >= out_of_stock_interval:
                message = "⚠️ Aún no hay stock del producto. Seguimos verificando..."
                send_telegram_notification(message)
                last_out_of_stock_notification_time = current_time  # Actualizar el tiempo

        # Esperar 5 minutos antes de volver a verificar
        time.sleep(300)

if __name__ == "__main__":
    main()