import os
import time
import logging
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from telegram import Bot

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Telegram config
TELEGRAM_BOT_TOKEN = "TU_TOKEN"
TELEGRAM_CHAT_ID = "TU_CHAT_ID"

PRODUCT_URL = "https://www.decathlon.es/es/p/bicicleta-mtb-xc-race-940-s-ltd-azul-cuadro-carbono-suspension-total/_/R-p-361277?mc=8929013"
CHECK_INTERVAL = 600  # 10 minutos
HEARTBEAT_INTERVAL = 300  # 5 minutos

bot = Bot(token=TELEGRAM_BOT_TOKEN)

def send_telegram(msg):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        logging.info("✅ Notificación enviada.")
    except Exception as e:
        logging.error(f"❌ Error enviando notificación Telegram: {e}")

def setup_driver():
    chrome_options = Options()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    return driver

def check_stock(driver):
    try:
        driver.get(PRODUCT_URL)
        time.sleep(5)  # esperar a que cargue
        page = driver.page_source

        if "sku-selector__stock--inStock" in page:
            msg = f"✅ ¡Hay stock disponible!\n🔗 {PRODUCT_URL}"
            send_telegram(msg)
        else:
            msg = "❌ Sin stock por ahora."
            send_telegram(msg)

    except Exception as e:
        logging.error(f"❌ Error comprobando el stock: {e}")
        send_telegram(f"❌ Error comprobando stock: {e}")

def main():
    send_telegram("🟢 Script iniciado correctamente.")
    last_check = 0
    last_heartbeat = 0

    driver = setup_driver()

    try:
        while True:
            now = time.time()

            if now - last_check >= CHECK_INTERVAL:
                logging.info("🔍 Comprobando stock...")
                check_stock(driver)
                last_check = now

            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                send_telegram("✅ Script funcionando. Esperando próxima verificación...")
                last_heartbeat = now

            time.sleep(10)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
