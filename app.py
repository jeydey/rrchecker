import requests
from bs4 import BeautifulSoup
import logging
import random
import time
from datetime import datetime

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
CHECK_INTERVAL = 600  # Cada 10 minutos
SUMMARY_INTERVAL = 1800  # Resumen cada 30 minutos

# ScrapeOps
SCRAPEOPS_API_KEY = "24f71537-bc7e-4c74-a75b-76e910aa1ab5"
PROXY = {
    "http": f"http://scrapeops.country=us:{SCRAPEOPS_API_KEY}@residential-proxy.scrapeops.io:8181",
    "https": f"http://scrapeops.country=us:{SCRAPEOPS_API_KEY}@residential-proxy.scrapeops.io:8181"
}

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Historial para resumen
check_history = []

# Obtener User-Agent aleatorio desde ScrapeOps
def get_random_user_agent():
    try:
        response = requests.get(
            url='https://headers.scrapeops.io/v1/browser-headers',
            params={
                'api_key': SCRAPEOPS_API_KEY,
                'num_results': '1'
            }
        )
        headers = response.json().get('result', [])
        return headers[0]['User-Agent'] if headers else None
    except Exception as e:
        logging.error(f"Error al obtener User-Agent: {e}")
        return None

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
        logging.error(f"Error al enviar notificación a Telegram: {e}")

def fetch_page():
    user_agent = get_random_user_agent()
    headers = {'User-Agent': user_agent} if user_agent else {}

    try:
        response = requests.get(PRODUCT_URL, headers=headers, proxies=PROXY, timeout=20, verify=False)
        response.raise_for_status()
        return response.text, user_agent, "ScrapeOps Proxies"
    except Exception as e:
        logging.error(f"Error al obtener página usando proxies: {e}")
        send_telegram_notification(f"❌ Error al obtener página:\n{e}")
        return None, user_agent, "ScrapeOps Proxies"

def check_stock():
    now = datetime.now().strftime('%H:%M:%S')
    logging.info("🔄 Verificando stock...")

    html, user_agent, metodo = fetch_page()
    if html:
        soup = BeautifulSoup(html, "html.parser")
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

        if not size_selector:
            message = f"🕒 [{now}]\n⚠️ No se encontró el selector de tallas.\n🔧 Método: {metodo}\n🧭 User-Agent: {user_agent}"
            logging.warning("No se encontró el selector de tallas.")
            send_telegram_notification(message)
            check_history.append((now, "⚠️ Sin selector", metodo, user_agent))
            return False

        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        if in_stock:
            message = (
                f"🕒 [{now}]\n🎉 ¡STOCK DISPONIBLE!\n🔗 {PRODUCT_URL}\n"
                f"🔧 Método: {metodo}\n🧭 User-Agent: {user_agent}"
            )
            send_telegram_notification(message)
            return True
        else:
            message = (
                f"🕒 [{now}]\n📦 Resultado: SIN STOCK\n✅ Página cargada correctamente\n"
                f"🔧 Método: {metodo}\n🧭 User-Agent: {user_agent}"
            )
            logging.info("Producto sin stock.")
            check_history.append((now, "❌ SIN STOCK", metodo, user_agent))
            return False
    else:
        check_history.append((now, "❌ ERROR", metodo, user_agent))
        return False

def send_summary():
    message = "📊 Resumen de actividad (últimos 30 minutos)\n"
    for check in check_history:
        hora, resultado, metodo, ua = check
        message += f"\n🕒 {hora} - {resultado}\n🔧 {metodo}\n🧭 {ua[:60]}..."
    message += "\n\n📡 Script funcionando correctamente."
    send_telegram_notification(message)
    check_history.clear()

def main():
    logging.info("✅ Script iniciado. Verificación cada 10 minutos.")
    send_telegram_notification("✅ El script está operativo y verificando stock cada 10 minutos. Resumen cada 30 minutos.")

    last_summary_time = time.time()

    while True:
        if check_stock():
            logging.info("¡Producto disponible! (notificado)")
        if time.time() - last_summary_time >= SUMMARY_INTERVAL:
            send_summary()
            last_summary_time = time.time()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()