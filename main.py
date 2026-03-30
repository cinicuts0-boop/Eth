from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = "8562765008:AAG4-qmd9949TGGQ7F5nGkOMMhXBdZlm8Ng"
CHAT_ID = "8007854479"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    message = f"""
🚀 ETH SIGNAL

Type: {data.get('type')}
Price: {data.get('price')}
Time: {data.get('time')}
"""
    send_telegram(message)
    return {"status": "ok"}

app.run(host="0.0.0.0", port=8080)
