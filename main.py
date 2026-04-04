# 🔹 STYLE (ULTRA MOBILE FRIENDLY)
def style():
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {
        background:#0f172a;
        color:#FFD700;
        font-family:Arial;
        margin:0;
        padding:0;
        text-align:center;
    }

    h2 {font-size:22px;margin-top:10px;}
    h3 {font-size:18px;}

    .nav {
        display:flex;
        justify-content:center;
        flex-wrap:wrap;
        gap:10px;
        margin:10px;
    }

    .nav a {
        padding:8px 12px;
        background:#1e293b;
        border-radius:8px;
        color:#FFD700;
        text-decoration:none;
        font-size:14px;
    }

    .grid {
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
        gap:12px;
        padding:12px;
    }

    .card {
        background:#1e293b;
        padding:15px;
        border-radius:12px;
        box-shadow:0 0 10px rgba(0,0,0,0.5);
    }

    .card h3 {
        margin:5px 0;
        font-size:18px;
    }

    .card p {
        margin:5px 0;
        font-size:14px;
    }

    .green {color:#22c55e;font-weight:bold;}
    .red {color:#ef4444;font-weight:bold;}

    .box {
        background:#1e293b;
        margin:10px;
        padding:15px;
        border-radius:10px;
        font-size:14px;
    }

    iframe {
        width:100%;
        height:250px;
        border:none;
    }
    </style>
    """

# 🔹 HEADER (IMPROVED NAV)
def header():
    return """
    <h2>🚀 Mani Money Mindset</h2>
    <div class="nav">
        <a href="/">🏠 Home</a>
        <a href="/signals">📩 Signals</a>
        <a href="/rules">📜 Rules</a>
    </div>
    <hr>
    """

# 🔹 HOME (SMALL IMPROVEMENT)
@app.route("/")
def home():
    cards = ""
    for coin, d in latest_data.items():

        color = ""
        if d["signal"] == "BUY":
            color = "green"
        elif d["signal"] == "SELL":
            color = "red"

        cards += f"""
        <a href="/coin/{coin}">
        <div class="card">
        <h3>{coin}</h3>
        <p>₹ {d['price']}</p>
        <p class="{color}">{d['signal']}</p>
        </div>
        </a>
        """

    return f"<html>{style()}<body>{header()}<div class='grid'>{cards}</div></body></html>"

# 🔹 SIGNAL PAGE (BOX STYLE)
@app.route("/signals")
def signals():
    msgs = "".join([
        f"<div class='box'>{m['time']} → {m['msg']}</div>"
        for m in telegram_messages[::-1][:50]
    ])
    return f"<html>{style()}<body>{header()}<h3>📩 Signals</h3>{msgs}</body></html>"

# 🔹 RULES
@app.route("/rules")
def rules():
    return f"""
    <html>{style()}
    <body>{header()}
    <div class='box'>
    <h3>📜 Rules</h3>
    <p>Trade at your own risk ⚠️</p>
    </div>
    </body></html>
    """

# 🔹 COIN PAGE (CLEAN LOOK)
@app.route("/coin/<name>")
def coin(name):
    d = latest_data.get(name, {})
    total, wins, loss, pnl, acc = calculate_stats()

    history = "".join([
        f"<div class='box'>{t['time']} | {t['type']} → {t['result']}</div>"
        for t in trade_history if t["coin"] == name
    ][-10:])

    return f"""
    <html>{style()}
    <body>{header()}

    <h2>{name}</h2>

    <div class="box">
    <p>Price: {d.get('price')}</p>
    <p>RSI: {d.get('rsi')}</p>
    <p>Signal: {d.get('signal')}</p>
    </div>

    <div class="box">
    <h3>📊 Performance</h3>
    <p>Accuracy: {acc}%</p>
    <p>PnL: {pnl}</p>
    </div>

    <h3>📜 History</h3>
    {history if history else "<p>No trades</p>"}

    </body></html>
    """
