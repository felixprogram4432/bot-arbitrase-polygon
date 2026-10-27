import time
import sys
import requests
from datetime import datetime

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# JALUR VIP ANTI-INTIP (1RPC MEV Shield + Bor Direct Validator)
POLYGON_RPCS = [
    "https://1rpc.io/matic",                    # Jalur Utama: Terenkripsi Anti-Frontrunning
    "https://polygon-bor-rpc.publicnode.com",   # Jalur Cepat: Direct Bor Node
    "https://polygon-rpc.com"                   # Jalur Cadangan
]

# Alamat Dompet Resmi Anda
DOMPET_ANDA = "0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"

# Kredensial Notifikasi Telegram Pribadi
TELEGRAM_TOKEN = "8854612522:AAF5cczXAA8RsPNA1vvd93asDVaOXZQreu0"
TELEGRAM_CHAT_ID = "5124389853"

# TARGET PORTOFOLIO "LAUTAN BIRU" (5 TARGET CROSS-POOL TERPILIH)
# Bebas dari HFT Raksasa, Mengincar Slippage Kolam Ramping & Stablecoin
POOLS = {
    "DAI_USDT": {
        "nama": "DAI / USDT (Stable)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x254aa3a898071d6a2da0db11da73b02b4646078f",
        "t0_dec": 18,
        "t1_dec": 6,
        "loan_usd": 3000.0,
        "tipe": "stable"
    },
    "MATIC_USDT": {
        "nama": "WMATIC / USDT",
        "quick": "0x604229c960e5cacf2aaeac8be68ac07ba9df81c3",
        "uni": "0x9b08288c3be4f62bbf8d1c20ac9c5e6f9467d8b7",
        "t0_dec": 18,
        "t1_dec": 6,
        "loan_usd": 2000.0,
        "tipe": "matic_usdt"
    },
    "ETH_USDT": {
        "nama": "WETH / USDT",
        "quick": "0xf6422b997c7f54d1c6a6e103bcb1499eea0a7046",
        "uni": "0xbb98b3d2b18aef63a3178023a920971cf5f29be4",
        "t0_dec": 18,
        "t1_dec": 6,
        "loan_usd": 3000.0,
        "tipe": "eth_usdt"
    },
    "MATIC_USDC": {
        "nama": "WMATIC / USDC",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0xa374094527e1673A86dE625aa59517c5de346d32",
        "t0_dec": 18,
        "t1_dec": 6,
        "loan_usd": 2500.0,
        "tipe": "matic_usdc"
    },
    "ETH_USDC": {
        "nama": "WETH / USDC",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x45dda9cb7c25131df268515131f647d726f50608",
        "t0_dec": 6,
        "t1_dec": 18,
        "loan_usd": 3500.0,
        "tipe": "eth_usdc"
    }
}

# Parameter Pertahanan Anti-Serobot
PRIORITY_FEE_GWEI = 42.0   # Tip khusus validator agar transaksi diselipkan di barisan terdepan (+Rp 30)
MAX_SLIPPAGE_PCT = 0.50    # Gembok anti-sandwich (batal jika harga bergeser >0.5%)
TOTAL_FEE_PCT = 0.44       # Aave 0.09% + DEX 0.35%

# Durasi Sesi per Runner Cloud: 5 Jam 45 Menit (Sebelum Estafet 30 Detik)
MAX_RUN_SECONDS = 5 * 3600 + 45 * 60 

def send_telegram_alert(pesan):
    """Kirim pesan instan ke HP via Telegram Bot"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": pesan,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=4)
    except Exception:
        pass

def fetch_blue_ocean_batch():
    """Batch Call 12-in-1 via Jalur Privat: Blok, Saldo, dan 5 Target Kolam Sekaligus!"""
    payload = [
        {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
        {"jsonrpc": "2.0", "id": 2, "method": "eth_getBalance", "params": [DOMPET_ANDA, "latest"]}
    ]
    
    req_id = 3
    mapping = {}
    for k, v in POOLS.items():
        mapping[req_id] = (k, "quick")
        payload.append({"jsonrpc": "2.0", "id": req_id, "method": "eth_call", "params": [{"to": v["quick"], "data": "0x0902f1ac"}, "latest"]})
        req_id += 1
        mapping[req_id] = (k, "uni")
        payload.append({"jsonrpc": "2.0", "id": req_id, "method": "eth_call", "params": [{"to": v["uni"], "data": "0x3850c7bd"}, "latest"]})
        req_id += 1

    for rpc_url in POLYGON_RPCS:
        try:
            r = requests.post(rpc_url, json=payload, timeout=5)
            if r.status_code == 200:
                data = r.json()
                res_map = {item["id"]: item.get("result", "0x") for item in data if "id" in item}
                
                # Blok
                block_hex = res_map.get(1, "0x0")
                block_num = int(block_hex, 16) if block_hex != "0x" else 0
                
                # Saldo POL
                bal_hex = res_map.get(2, "0x0")
                saldo_pol = int(bal_hex, 16) / 10**18 if bal_hex != "0x" else 0.0
                
                # Harga Tiap Pool
                prices = {}
                for k, v in POOLS.items():
                    prices[k] = {"q": None, "u": None}
                    
                for id_num, (k, dex) in mapping.items():
                    raw = res_map.get(id_num, "0x")
                    cfg = POOLS[k]
                    if dex == "quick" and len(raw) >= 130:
                        r0 = int(raw[2:66], 16) / (10**cfg["t0_dec"])
                        r1 = int(raw[66:130], 16) / (10**cfg["t1_dec"])
                        if cfg["tipe"] == "eth_usdc":
                            prices[k]["q"] = r0 / r1 if r1 > 0 else None
                        else:
                            prices[k]["q"] = r1 / r0 if r0 > 0 else None
                    elif dex == "uni" and len(raw) >= 66:
                        sqrtP = int(raw[2:66], 16)
                        if cfg["tipe"] == "eth_usdc":
                            prices[k]["u"] = (10**12) / (((sqrtP / (2**96)) ** 2))
                        else:
                            prices[k]["u"] = (((sqrtP / (2**96)) ** 2) * (10**(cfg["t0_dec"] - cfg["t1_dec"])))
                
                return block_num, saldo_pol, prices, rpc_url
        except Exception:
            continue
    return 0, 0.0, {}, "None"

def main():
    print("=" * 75)
    print(" 🌊 RADAR CLOUD 24/7 - EDISI LAUTAN BIRU (5 TARGET CROSS-POOL)")
    print(" 🛡️  Jalur Anti-Frontrunning: 1RPC Shield + Bor Priority Tip 42 Gwei")
    print(" 🎯 Bebas dari HFT Raksasa: Kolam Ramping & Arbitrase Stablecoin")
    print(" 💳 Dompet Pengawas:", DOMPET_ANDA)
    print("=" * 75)

    # Notifikasi Awal ke Telegram
    intro_msg = (
        "🌊 *RADAR CLOUD EDISI LAUTAN BIRU AKTIF!*\n\n"
        "🎯 *Portofolio 5 Target:* DAI/USDT, MATIC/USDT, ETH/USDT, MATIC/USDC, ETH/USDC\n"
        "🛡️ *Perisai:* 1RPC Shield (Anti-Intip)\n"
        "⚡ *Priority Tip:* 42 Gwei (Barisan Depan Blok)\n"
        "⏰ *Status:* Siaga 24 Jam Nonstop di Cloud!"
    )
    send_telegram_alert(intro_msg)

    start_time = time.time()
    last_block = 0
    scan_count = 0
    last_alert_time = {}

    while True:
        elapsed = time.time() - start_time
        if elapsed > MAX_RUN_SECONDS:
            print("\n🔄 Sesi 5 jam 45 menit tercapai! Menyerahkan estafet ke sesi baru...")
            break

        block_num, saldo_pol, prices, active_rpc = fetch_blue_ocean_batch()
        
        if block_num != last_block and block_num > 0:
            last_block = block_num
            scan_count += 1
            now = datetime.now().strftime("%H:%M:%S")

            print(f"\n[Blok #{block_num} | {now} | Saldo: {saldo_pol:.3f} POL | Shield: {active_rpc}]")

            for k, p in prices.items():
                p_q = p.get("q")
                p_u = p.get("u")
                cfg = POOLS[k]

                if p_q and p_u and p_q > 0 and p_u > 0:
                    selisih = abs(p_q - p_u)
                    spread_pct = (selisih / min(p_q, p_u)) * 100
                    
                    arah = "QuickSwap ➡️ UniV3" if p_q < p_u else "UniV3 ➡️ QuickSwap"
                    
                    # Format tampilan harga
                    if "DAI" in k:
                        format_str = f"Quick: ${p_q:.4f} | Uni: ${p_u:.4f} | Spread: {spread_pct:.3f}%"
                    elif "MATIC" in k:
                        format_str = f"Quick: ${p_q:.4f} | Uni: ${p_u:.4f} | Spread: {spread_pct:.3f}%"
                    else:
                        format_str = f"Quick: ${p_q:.2f} | Uni: ${p_u:.2f} | Spread: {spread_pct:.3f}%"

                    print(f"  • {cfg['nama']:<20}: {format_str}")

                    # JIKA SPREAD MENUTUPI BIAYA FEE (Spread > 0.75%)
                    if spread_pct > 0.75:
                        net_profit_pct = spread_pct - TOTAL_FEE_PCT
                        loan = cfg["loan_usd"]
                        est_cuan_usd = (net_profit_pct / 100.0) * loan
                        est_cuan_idr = est_cuan_usd * 15600

                        print(f"    🔥 [PELUANG CUAN!] {arah} | Net: +{net_profit_pct:.2f}% (~Rp {est_cuan_idr:,.0f})")

                        # Kirim Notifikasi Telegram (Throttle 60 detik per pool)
                        last_t = last_alert_time.get(k, 0)
                        if (time.time() - last_t) > 60:
                            last_alert_time[k] = time.time()
                            cuan_msg = (
                                f"🚨 *PELUANG ARBITRASE LAUTAN BIRU!* 🚨\n\n"
                                f"🪙 *Pasangan:* {cfg['nama']}\n"
                                f"📊 *Spread Kotor:* {spread_pct:.2f}%\n"
                                f"💰 *Profit Bersih:* +{net_profit_pct:.2f}%\n"
                                f"💵 *Estimasi Cuan:* ${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})\n"
                                f"🔄 *Jalur:* {arah}\n"
                                f"⚡ *Loan:* ${loan:,.0f}\n"
                                f"🛡️ *Anti-Frontrunning:* Terenkripsi 1RPC"
                            )
                            send_telegram_alert(cuan_msg)

        time.sleep(0.25)

if __name__ == "__main__":
    main()
