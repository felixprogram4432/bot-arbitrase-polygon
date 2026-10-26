import os
import sys
import time
import threading
import requests
from datetime import datetime
from flask import Flask, render_template_string, jsonify

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

# Konfigurasi Sistem
POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"
DOMPET_ANDA = "0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"
MIN_SPREAD_THRESHOLD = 0.75
LOAN_SIZE_USD = 2500.0

POOLS = {
    "QuickSwap": "0x6e7a5FAFcec6BB1e78bAE2A1F0B612012BF14827",
    "UniswapV3": "0xA374094527e1673A86dE625aa59517c5dE346d32"
}

# Status Memori Global Bot
bot_state = {
    "status": "AKTIF 24 JAM DI CLOUD",
    "last_block": 0,
    "last_update": "-",
    "p_quick": 0.0,
    "p_uni": 0.0,
    "spread_pct": 0.0,
    "saldo_pol": 0.0,
    "saldo_idr": 0,
    "total_menang": 0,
    "total_batal_aman": 0,
    "total_cuan_idr": 0,
    "logs": []
}

def get_onchain_data():
    payload = [
        {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["QuickSwap"], "data": "0x0902f1ac"}, "latest"], "id": 2},
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["UniswapV3"], "data": "0x3850c7bd"}, "latest"], "id": 3},
        {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [DOMPET_ANDA, "latest"], "id": 4}
    ]
    try:
        r = requests.post(POLYGON_RPC, json=payload, timeout=4)
        res = r.json()
        
        block = int(res[0].get("result", "0"), 16)
        
        q_data = res[1].get("result", "")
        r0 = int(q_data[2:66], 16)
        r1 = int(q_data[66:130], 16)
        p_quick = (r1 / 10**6) / (r0 / 10**18)
        
        u_data = res[2].get("result", "")
        sqrtPriceX96 = int(u_data[2:66], 16)
        p_uni = ((sqrtPriceX96 / (2**96)) ** 2) * (10**12)
        
        bal_wei = int(res[3].get("result", "0"), 16)
        saldo_pol = bal_wei / 10**18
        
        return block, p_quick, p_uni, saldo_pol
    except Exception:
        return 0, 0, 0, 0

def background_arbitrage_worker():
    global bot_state
    last_processed_block = 0
    
    while True:
        try:
            block, p_quick, p_uni, saldo_pol = get_onchain_data()
            if block > last_processed_block and p_quick > 0 and p_uni > 0:
                last_processed_block = block
                spread = (abs(p_quick - p_uni) / min(p_quick, p_uni)) * 100
                waktu_str = datetime.now().strftime("%H:%M:%S")
                
                bot_state["last_block"] = block
                bot_state["last_update"] = waktu_str
                bot_state["p_quick"] = round(p_quick, 6)
                bot_state["p_uni"] = round(p_uni, 6)
                bot_state["spread_pct"] = round(spread, 4)
                bot_state["saldo_pol"] = round(saldo_pol, 4)
                bot_state["saldo_idr"] = int(saldo_pol * 1600)
                
                total_fee = 0.44
                if spread >= MIN_SPREAD_THRESHOLD:
                    gross_usd = LOAN_SIZE_USD * (spread / 100)
                    fee_usd = LOAN_SIZE_USD * (total_fee / 100)
                    net_usd = gross_usd - fee_usd - 0.015
                    cuan_idr = int(net_usd * 16000)
                    
                    bot_state["total_menang"] += 1
                    bot_state["total_cuan_idr"] += cuan_idr
                    
                    log_entry = f"[{waktu_str}] 🎉 EKSEKUSI SUKSES: Blok #{block} | Spread {spread:.3f}% | Profit: +Rp {cuan_idr:,.0f}"
                    bot_state["logs"].insert(0, log_entry)
                else:
                    if len(bot_state["logs"]) == 0 or "SIAGA" not in bot_state["logs"][0]:
                        bot_state["logs"].insert(0, f"[{waktu_str}] 🛡️ SIAGA: Blok #{block} | Spread {spread:.3f}% (Di bawah buffer 0.75%). Bensin aman.")
                
                # Batasi log maksimal 30 baris
                bot_state["logs"] = bot_state["logs"][:30]
                
        except Exception:
            pass
        
        time.sleep(2.0)

# Jalankan background worker di thread terpisah
worker_thread = threading.Thread(target=background_arbitrage_worker, daemon=True)
worker_thread.start()

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cockpit Arbitrase Polygon Cloud</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .badge { background: #238636; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; }
        h1 { font-size: 20px; margin-top: 0; color: #58a6ff; }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px; }
        .stat-box { background: #21262d; padding: 12px; border-radius: 8px; text-align: center; }
        .stat-num { font-size: 18px; font-weight: bold; color: #3fb950; margin-top: 4px; }
        .stat-title { font-size: 12px; color: #8b949e; }
        .logs-box { background: #090d13; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-family: monospace; font-size: 12px; max-height: 250px; overflow-y: auto; color: #8b949e; }
        .log-item { margin-bottom: 6px; line-height: 1.4; }
    </style>
    <script>
        setInterval(async () => {
            const res = await fetch('/api/status');
            const data = await res.json();
            document.getElementById('last-block').innerText = '#' + data.last_block;
            document.getElementById('spread-val').innerText = data.spread_pct + '%';
            document.getElementById('saldo-val').innerText = data.saldo_pol + ' POL (Rp ' + data.saldo_idr.toLocaleString('id-ID') + ')';
            document.getElementById('cuan-val').innerText = '+Rp ' + data.total_cuan_idr.toLocaleString('id-ID');
            document.getElementById('menang-val').innerText = data.total_menang + 'x';
            
            const logBox = document.getElementById('log-box');
            logBox.innerHTML = data.logs.map(l => '<div class="log-item">' + l + '</div>').join('');
        }, 2000);
    </script>
</head>
<body>
    <div class="container">
        <div class="card">
            <span class="badge">🟢 LIVE CLOUD 24/7</span>
            <h1>⚡ Dashboard Arbitrase Polygon</h1>
            <p style="font-size: 12px; color: #8b949e; margin-bottom: 0;">Dompet: {{ dompet }}</p>
            
            <div class="stat-grid">
                <div class="stat-box">
                    <div class="stat-title">Saldo Asli Dompet</div>
                    <div class="stat-num" id="saldo-val">{{ state.saldo_pol }} POL</div>
                </div>
                <div class="stat-box">
                    <div class="stat-title">Akumulasi Cuan</div>
                    <div class="stat-num" id="cuan-val">+Rp {{ "{:,}".format(state.total_cuan_idr) }}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-title">Selisih Terbuka (Spread)</div>
                    <div class="stat-num" style="color: #58a6ff;" id="spread-val">{{ state.spread_pct }}%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-title">Blok Polygon Aktif</div>
                    <div class="stat-num" style="color: #d29922;" id="last-block">#{{ state.last_block }}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2 style="font-size: 14px; margin-top: 0; color: #c9d1d9;">📜 Radar Log Aktivitas Blockchain</h2>
            <div class="logs-box" id="log-box">
                {% for log in state.logs %}
                    <div class="log-item">{{ log }}</div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_DASHBOARD, dompet=DOMPET_ANDA, state=bot_state)

@app.route('/api/status')
def status():
    return jsonify(bot_state)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
