import requests
from bs4 import BeautifulSoup
import logging
import random
import time

# Configuración inicial
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"
CHECK_INTERVAL = 600  # Comprobación de stock cada 10 minutos (600 seg)
STATUS_NOTIFICATION_INTERVAL = 1800  # Reporte de estado cada 30 minutos

# ScrapeOps
SCRAPEOPS_API_KEY = "24f71537-bc7e-4c74-a75b-76e910aa1ab5"
PROXY_URL = f"http://scrapeops.country=us:{SCRAPEOPS_API_KEY}@residential-proxy.scrapeops.io:8181"

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Historial de comprobaciones
check_results = []
last_status_notification = time.time()


def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("📬 Notificación enviada a Telegram.")
        else:
            logging.error(f"❌ Error al enviar notificación a Telegram: {response.text}")
    except Exception as e:
        logging.error(f"❌ Error al enviar notificación a Telegram: {e}")


def get_random_user_agent():
    try:
        headers_api = "https://headers.scrapeops.io/v1/browser-headers"
        response = requests.get(headers_api, params={
            'api_key': SCRAPEOPS_API_KEY,
            'num_results': 1
        }, timeout=10)
        response.raise_for_status()
        return response.json()['result'][0]['User-Agent']
    except Exception as e:
        logging.warning(f"⚠️ No se pudo obtener User-Agent dinámico: {e}")
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"


def fetch_with_proxy():
    try:
        headers = {'User-Agent': get_random_user_agent()}
        proxies = {
            "http": PROXY_URL,
            "https": PROXY_URL
        }
        response = requests.get(PRODUCT_URL, proxies=proxies, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        logging.info("✅ Página obtenida correctamente con proxy directo.")
        return response.content
    except Exception as e:
        logging.warning(f"⚠️ Fallo con proxy directo: {e}")
        return None


def fetch_with_scrapeops_api():
    try:
        response = requests.get(
            url='https://proxy.scrapeops.io/v1/',
            params={
                'api_key': SCRAPEOPS_API_KEY,
                'url': PRODUCT_URL,
                'render_js': 'true',
                'residential': 'true',
                'country': 'us',
            },
            timeout=30
        )
        response.raise_for_status()
        logging.info("✅ Página obtenida correctamente con ScrapeOps API.")
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error con ScrapeOps API: {e}")
        return None


def check_stock():
    logging.info("🔍 Iniciando verificación de stock...")
    page_content = fetch_with_proxy()
    if not page_content:
        page_content = fetch_with_scrapeops_api()
    if not page_content:
        logging.error("❌ No se pudo obtener la página con ninguno de los métodos.")
        check_results.append("❌ Fallo en verificación")
        return False

    soup = BeautifulSoup(page_content, "html.parser")
    size_selector = soup.find("ul", class_="vtmn-sku-selector__items")

    if not size_selector:
        message = "⚠️ Selector de tallas no encontrado."
        logging.warning(message)
        check_results.append("⚠️ Sin selector de tallas")
        return False

    in_stock = any(
        "sku-selector__stock--inStock" in str(item)
        for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
    )

    if in_stock:
        message = "🎉 ¡STOCK DISPONIBLE! Corre a comprar 🛒"
        logging.info(message)
        send_telegram_notification(message)
        check_results.append("✅ ¡STOCK DISPONIBLE!")
        return True
    else:
        logging.info("❌ Producto sin stock.")
        check_results.append("❌ Sin stock")
        return False


def send_status_summary():
    global check_results
    if check_results:
        resumen = "📝 Resumen de las últimas verificaciones:\n"
        for i, result in enumerate(check_results, 1):
            resumen += f"{i}. {result}\n"
        send_telegram_notification(resumen.strip())
        check_results = []


def main():
    global last_status_notification
    logging.info("🚀 Script iniciado correctamente.")
    send_telegram_notification("✅ Script iniciado y monitoreando stock cada 10 minutos.")

    while True:
        result = check_stock()

        current_time = time.time()
        if current_time - last_status_notification > STATUS_NOTIFICATION_INTERVAL:
            send_status_summary()
            last_status_notification = current_time

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
