import time
import sys
import requests
from datetime import datetime

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Multi-RPC Jalur Kilat (Prioritas Node Tercepat)
POLYGON_RPCS = [
    "https://polygon-bor-rpc.publicnode.com",
    "https://1rpc.io/matic",
    "https://polygon-rpc.com"
]

# Alamat Dompet Resmi Anda
DOMPET_ANDA = "0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"

# Kredensial Notifikasi Telegram Pribadi
TELEGRAM_TOKEN = "8854612522:AAF5cczXAA8RsPNA1vvd93asDVaOXZQreu0"
TELEGRAM_CHAT_ID = "5124389853"

# TARGET IDEAL "TRIO RAKSASA": MATIC + ETHEREUM + BITCOIN DI POLYGON
POOLS = {
    "MATIC": {
        "nama": "WMATIC / USDC",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0xa374094527e1673a86de625aa59517c5de346d32",
        "loan_usd": 2500.0,
        "type": "matic"
    },
    "ETH": {
        "nama": "WETH / USDC",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x45dda9cb7c25131df268515131f647d726f50608",
        "loan_usd": 3500.0,
        "type": "eth"
    },
    "BTC": {
        "nama": "WBTC / USDC",
        "quick": "0xf6a637525402643b0654a54bead2cb9a83c8b498",
        "uni": "0x847b64f9d3a95e977d157866447a5c0a5dfa0ee5",
        "loan_usd": 5000.0,
        "type": "btc"
    }
}

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

def fetch_trio_batch():
    """Batch Call 7-in-1: Baca Blok, Saldo, dan 3 Pasang Koin Raksasa Sekaligus dalam 1 Paket Kilat!"""
    payload = [
        {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
        {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [DOMPET_ANDA, "latest"], "id": 2},
        # MATIC
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["MATIC"]["quick"], "data": "0x0902f1ac"}, "latest"], "id": 3},
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["MATIC"]["uni"], "data": "0x3850c7bd"}, "latest"], "id": 4},
        # ETH
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["ETH"]["quick"], "data": "0x0902f1ac"}, "latest"], "id": 5},
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["ETH"]["uni"], "data": "0x3850c7bd"}, "latest"], "id": 6},
        # BTC
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["BTC"]["quick"], "data": "0x0902f1ac"}, "latest"], "id": 7},
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["BTC"]["uni"], "data": "0x3850c7bd"}, "latest"], "id": 8}
    ]
    
    for rpc in POLYGON_RPCS:
        try:
            r = requests.post(rpc, json=payload, timeout=2.2)
            res = r.json()
            
            block = int(res[0].get("result", "0"), 16)
            bal_wei = int(res[1].get("result", "0"), 16)
            saldo_pol = bal_wei / 10**18
            
            # 1. MATIC Price
            qm = res[2].get("result", "")
            r0_m, r1_m = int(qm[2:66], 16), int(qm[66:130], 16)
            p_matic_q = (r1_m / 10**6) / (r0_m / 10**18)
            um = res[3].get("result", "")
            sq_m = int(um[2:66], 16)
            p_matic_u = ((sq_m / (2**96)) ** 2) * (10**12)
            
            # 2. ETH Price
            qe = res[4].get("result", "")
            r0_e, r1_e = int(qe[2:66], 16), int(qe[66:130], 16)
            p_eth_q = (r0_e / 10**6) / (r1_e / 10**18)
            ue = res[5].get("result", "")
            sq_e = int(ue[2:66], 16)
            p_eth_u = (1.0 / ((sq_e / (2**96)) ** 2)) * (10**12)
            
            # 3. BTC Price
            qb = res[6].get("result", "")
            r0_b, r1_b = int(qb[2:66], 16), int(qb[66:130], 16)
            p_btc_q = (r1_b / 10**6) / (r0_b / 10**8)
            ub = res[7].get("result", "")
            sq_b = int(ub[2:66], 16)
            p_btc_u = (((sq_b / (2**96)) ** 2)) * (10**2)
            
            prices = {
                "MATIC": {"q": p_matic_q, "u": p_matic_u},
                "ETH":   {"q": p_eth_q,   "u": p_eth_u},
                "BTC":   {"q": p_btc_q,   "u": p_btc_u}
            }
            
            return block, saldo_pol, prices, rpc
        except Exception:
            continue
            
    return 0, 0, {}, ""

def main():
    start_time = time.time()
    
    print("=" * 80, flush=True)
    print(" 🔱 RADAR ARBITRASE CLOUD 24/7 - TRIO RAKSASA (MATIC + ETH + BTC) 🔱", flush=True)
    print(f"   Alamat Dompet : {DOMPET_ANDA}", flush=True)
    print("   Target Pasang : WMATIC/USDC | WETH/USDC | WBTC/USDC", flush=True)
    print("   Kecepatan     : Super Kilat Batch 7-in-1 (Polling 0.25 Detik)", flush=True)
    print("=" * 80, flush=True)
    
    send_telegram_alert(
        "🔱 *RADAR TRIO RAKSASA (MATIC + ETH + BTC) RESMI AKTIF!*\n\n"
        "⚡ 3 Jaring Raksasa Terpasang Sekaligus:\n"
        "• 🟣 *WMATIC/USDC*\n"
        "• 🔵 *WETH/USDC* (Ethereum)\n"
        "• 🟡 *WBTC/USDC* (Bitcoin)\n\n"
        "🏎️ *Kecepatan:* Polling 0.25s (Bensin tetap Rp 250 POL!).\n"
        f"👛 *Dompet:* `{DOMPET_ANDA[:6]}...{DOMPET_ANDA[-4:]}`"
    )
    
    last_block = 0
    last_telegram_time = {}
    
    while True:
        try:
            # Periksa estafet 5 jam 45 menit
            elapsed = time.time() - start_time
            if elapsed >= MAX_RUN_SECONDS:
                print("\n[ESTAFET] Sesi 5 jam 45 menit tercapai! Menyerahkan tongkat estafet ke server baru...", flush=True)
                send_telegram_alert("🔄 *[ESTAFET KILAT]* Mengoper tongkat estafet ke server cloud baru sekarang...")
                break
                
            t0 = time.perf_counter()
            block, saldo_asli_pol, prices, active_rpc = fetch_trio_batch()
            latency_sec = time.perf_counter() - t0
            
            if block > last_block and len(prices) == 3:
                last_block = block
                waktu = datetime.now().strftime("%H:%M:%S")
                saldo_asli_idr = saldo_asli_pol * 1600
                total_fee_pct = 0.44
                
                print(f"\n[BLOK #{block} | {waktu}] (Latency: {latency_sec:.4f}s | Saldo: {saldo_asli_pol:.4f} POL)", flush=True)
                
                for koin_key, p_data in prices.items():
                    pq = p_data["q"]
                    pu = p_data["u"]
                    koin_info = POOLS[koin_key]
                    spread = (abs(pq - pu) / min(pq, pu)) * 100
                    
                    simbol = "🟣" if koin_key == "MATIC" else ("🔵" if koin_key == "ETH" else "🟡")
                    format_str = ".4f" if koin_key == "MATIC" else ".2f"
                    
                    print(f"  {simbol} {koin_info['nama']:<12} | Quick: ${pq:{format_str}} | Uni: ${pu:{format_str}} | Spread: {spread:.3f}%", flush=True)
                    
                    if spread > total_fee_pct:
                        loan = koin_info["loan_usd"]
                        gross_usd = loan * (spread / 100)
                        fee_usd = loan * (total_fee_pct / 100)
                        net_usd = gross_usd - fee_usd - 0.015
                        cuan_idr = net_usd * 16000
                        
                        print(f"     🎉 [CUAN TERDETEKSI DI {koin_key}!] Estimasi Bersih: +${net_usd:.2f} (+Rp {cuan_idr:,.0f})", flush=True)
                        
                        current_epoch = time.time()
                        last_t = last_telegram_time.get(koin_key, 0)
                        if current_epoch - last_t > 60:
                            last_telegram_time[koin_key] = current_epoch
                            msg = (
                                f"🎉 *PELUANG ARBITRASE DI {koin_key}!*\n\n"
                                f"🪙 *Pasangan:* `{koin_info['nama']}`\n"
                                f"⚡ *Blok:* `#{block}` | Jam: `{waktu}`\n"
                                f"📊 *Spread:* `{spread:.3f}%`\n"
                                f"💰 *Estimasi Cuan Bersih:* `+Rp {cuan_idr:,.0f} (+${net_usd:.2f})`\n"
                                f"👛 *Saldo Bensin:* `{saldo_asli_pol:.4f} POL`"
                            )
                            send_telegram_alert(msg)
                
                print("-" * 80, flush=True)
            
            time.sleep(0.25)
            
        except Exception:
            time.sleep(1.0)

if __name__ == "__main__":
    main()
