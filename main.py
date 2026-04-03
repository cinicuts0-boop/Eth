update_results()
            print("Updated...")
            time.sleep(300)  # 5 min
        except Exception as e:
            print("Bot Error:", e)
            time.sleep(60)

# 🔥 HOME PAGE
@app.route("/")
def dashboard():
    cards = ""
    for coin, data in latest_data.items():
        cards += f"""
        <a href="/coin/{coin}">
            <div class="box">
                <h2>{coin}</h2>
                <p>{data['price']}</p>
                <p class="{data['signal'].lower()}">{data['signal']}</p>
            </div>
        </a>
        """

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: #FFD700;
                text-align: center;
            }}

            h1 {{
                color: #FFD700;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 12px;
                padding: 12px;
            }}

            .box {{
                background: #1e293b;
                padding: 20px;
                border-radius: 15px;
                border: 1px solid #FFD700;
                box-shadow: 0 0 10px rgba(255,215,0,0.2);
                transition: 0.3s;
            }}

            .box:hover {{
                transform: scale(1.05);
            }}

            p {{
                color: #FFD700;
            }}

            .buy {{ color: #22c55e; }}
            .sell {{ color: #ef4444; }}

            a {{
                text-decoration: none;
            }}
        </style>
    </head>

    <body>

    <h1>🚀 Mani Money Mindset 💸</h1>
    <h4>  ꧁༺ 💚 எண்ணம் போல் வாழ்க்கை ❤️ ༻꧂ </h4>

    <div class="grid">
        {cards}
    </div>

    </body>
    </html>
    """


# 🔥 DETAIL PAGE
@app.route("/coin/<name>")
def coin_detail(name):
    data = latest_data.get(name, {})

    total, wins, loss, pnl, accuracy = calculate_stats()

    history_html = "".join([
        f"<p>{t['time']} | {t['coin']} {t['type']} @ {t['price']} → {t['result']}</p>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    chart_map = {
        "ETH": "BINANCE:ETHUSDT",
        "BTC": "BINANCE:BTCUSDT",
        "NIFTY": "NSE:NIFTY",
        "BANKNIFTY": "NSE:BANKNIFTY",
        "CRUDE": "NYMEX:CL1!"
    }

    symbol = chart_map.get(name)

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial;
                background: #0f172a;
                color: #FFD700;
                text-align: center;
            }}

            .box {{
                background: #1e293b;
                padding: 15px;
                border-radius: 15px;
                margin: 10px;
                border: 1px solid #FFD700;
            }}

            a {{
                color: #FFD700;
                text-decoration: none;
            }}
        </style>
    </head>

    <body>

    <h1>{name} DETAILS</h1>

    <div class="box">
        <p>Price: {data.get('price')}</p>
        <p>RSI: {data.get('rsi')}</p>
        <p>Signal: {data.get('signal')}</p>
    </div>

    <div class="box">
        <h3>📊 Performance</h3>
        <p>Accuracy: {accuracy}%</p>
        <p>PnL: {pnl}</p>
    </div>

    <div class="box">
        <h3>📈 Chart</h3>
        <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol}&interval=5&theme=dark"
        width="100%" height="300"></iframe>
    </div>

    <div class="box">
        <h3>📜 Trade History</h3>
        {history_html}
    </div>

    <br>
    <a href="/">⬅ Back</a>

    </body>
    </html>
    """


if name == "__main__":
    threading.Thread(target=run_bot).start()
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
