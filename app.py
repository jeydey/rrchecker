import requests
from bs4 import BeautifulSoup
import time
import random

# Configuración de la URL del producto
PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = "7930591359:AAG9UjjmyAcy7xGGzOyIHAqEgTUlAOZqj1w"
TELEGRAM_CHAT_ID = "871212552"

# Lista de proxies (reemplaza estos con proxies válidos)
PROXIES = [
    "http://proxy1:port",
    "http://proxy2:port",
    "http://proxy3:port"
]

def send_telegram_notification(message):
    try:
        # URL de la API de Telegram
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

def send_startup_notification():
    # Mensaje de inicio
    startup_message = "✅ El script está operativo y verificando stock cada 5 minutos."
    send_telegram_notification(startup_message)

def check_stock():
    try:
        # Seleccionar un proxy aleatorio
        proxy = random.choice(PROXIES)

        # Realizar la solicitud HTTP a la página del producto
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.5",
            "Referer": "https://www.decathlon.es/",
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        response = requests.get(PRODUCT_URL, headers=headers, proxies={"http": proxy, "https": proxy})
        response.raise_for_status()

        # Analizar el HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Buscar el selector de tallas
        size_selector = soup.find("ul", class_="vtmn-sku-selector__items")
        if not size_selector:
            print("No se encontró el selector de tallas.")
            return False

        # Verificar si alguna talla tiene stock
        in_stock = any(
            "sku-selector__stock--inStock" in str(item)
            for item in size_selector.find_all("li", class_="vtmn-sku-selector__item")
        )

        return in_stock

    except Exception as e:
        print(f"Error al verificar el stock: {e}")
        return False

def main():
    # Enviar mensaje de inicio
    send_startup_notification()

    while True:
        print("Verificando stock...")
        if check_stock():
            print("¡Producto disponible!")
            message = f"¡El producto está disponible!\n\nVisita: {PRODUCT_URL}"
            send_telegram_notification(message)
        else:
            print("Sin stock.")

        # Esperar 5 minutos antes de volver a verificar
        time.sleep(300)

if __name__ == "__main__":
    main()