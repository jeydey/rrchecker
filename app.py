import requests
import random
import time
import logging

# Configuración de ScrapeOps
SCRAPEOPS_API_KEY = "24f71537-bc7e-4c74-a75b-76e910aa1ab5"
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Función para enviar notificación a Telegram
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

# Función para comprobar stock usando ScrapeOps
def check_stock():
    """Comprobar el stock usando ScrapeOps."""
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
        )

        # Depurar el contenido para verificar qué se está extrayendo
        if response.status_code == 200:
            content = response.content.decode('utf-8')
            logging.info(f"Contenido recibido: {content[:1000]}...")  # Imprime los primeros 1000 caracteres para depuración

            # Buscamos si hay "sin stock" o "agotado" u otros indicadores de no disponibilidad
            if "sin stock" in content.lower() or "agotado" in content.lower():
                return False
            else:
                return True
        else:
            logging.error(f"Error al obtener la página de Decathlon: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al realizar la solicitud de stock: {e}")
        return False

# Función principal
def main():
    send_telegram_notification("✅ El script está operativo y verificando stock cada 10 minutos.")
    
    last_stock_check_time = 0
    last_telegram_message_time = 0

    while True:
        current_time = time.time()

        # Comprobación del stock cada 10 minutos
        if current_time - last_stock_check_time >= 600:  # 600 segundos = 10 minutos
            logging.info("Comprobando stock del producto...")
            if check_stock():
                send_telegram_notification(f"🎉 ¡Producto disponible! Consulta aquí: {PRODUCT_URL}")
            else:
                send_telegram_notification("❌ Falló la comprobación del stock. Intentando nuevamente en 10 minutos.")
            last_stock_check_time = current_time

        # Enviar mensaje cada 5 minutos sin comprobar el stock
        if current_time - last_telegram_message_time >= 300:  # 300 segundos = 5 minutos
            send_telegram_notification("🔄 El script sigue funcionando correctamente.")
            last_telegram_message_time = current_time

        # Espera para evitar usar demasiados recursos
        time.sleep(60)  # 60 segundos, para que el script siga funcionando sin sobrecargar el sistema

if __name__ == "__main__":
    main()
