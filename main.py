
import requests
import time

TELEGRAM_TOKEN = "8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng"
CHAT_ID = "8007854479"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    print(res.text)

print("Test Bot Started...")

while True:
    send_telegram("✅ TEST MESSAGE ETH BOT")
    time.sleep(60)
