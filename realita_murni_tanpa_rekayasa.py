import time
import sys
import requests
from datetime import datetime

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"

# Alamat Dompet Resmi Anda
DOMPET_ANDA = "0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"

# Kredensial Notifikasi Telegram Pribadi
TELEGRAM_TOKEN = "8854612522:AAF5cczXAA8RsPNA1vvd93asDVaOXZQreu0"
TELEGRAM_CHAT_ID = "5124389853"

# Kolam Likuiditas Nyata Polygon
POOLS = {
    "QuickSwap": "0x6e7a5FAFcec6BB1e78bAE2A1F0B612012BF14827",
    "UniswapV3": "0xA374094527e1673A86dE625aa59517c5dE346d32"
}

def send_telegram_alert(pesan):
    """Kirim pesan instan ke HP via Telegram Bot"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": pesan,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def get_live_wallet_balance(wallet_address):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [wallet_address, "latest"],
        "id": 10
    }
    try:
        r = requests.post(POLYGON_RPC, json=payload, timeout=3)
        bal_wei = int(r.json().get("result", "0"), 16)
        bal_pol = bal_wei / 10**18
        return bal_pol
    except Exception:
        return 0.0

def get_pure_onchain_data():
    payload = [
        {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["QuickSwap"], "data": "0x0902f1ac"}, "latest"], "id": 2},
        {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": POOLS["UniswapV3"], "data": "0x3850c7bd"}, "latest"], "id": 3}
    ]
    try:
        r = requests.post(POLYGON_RPC, json=payload, timeout=3)
        res = r.json()
        
        block = int(res[0].get("result", "0"), 16)
        
        q_data = res[1].get("result", "")
        r0 = int(q_data[2:66], 16)
        r1 = int(q_data[66:130], 16)
        p_quick = (r1 / 10**6) / (r0 / 10**18)
        
        u_data = res[2].get("result", "")
        sqrtPriceX96 = int(u_data[2:66], 16)
        p_uni = ((sqrtPriceX96 / (2**96)) ** 2) * (10**12)
        
        return block, p_quick, p_uni
    except Exception:
        return 0, 0, 0

def main():
    print("=" * 80, flush=True)
    print("      🎯 RADAR ARBITRASE CLOUD 24/7 + TELEGRAM NOTIFIKASI 🎯", flush=True)
    print(f"   Alamat Dompet : {DOMPET_ANDA}", flush=True)
    print("   Data Sumber   : Memori Smart Contract Polygon Asli (Block-by-Block)", flush=True)
    print("   Notifikasi    : Terhubung langsung ke Telegram Anda", flush=True)
    print("=" * 80, flush=True)
    
    # Kirim salam pembuka ke Telegram saat bot mulai aktif di cloud
    send_telegram_alert(
        "🟢 *BOT ARBITRASE CLOUD 24/7 RESMI AKTIF!*\n\n"
        "⚡ Radar sedang memindai blockchain Polygon tanpa henti.\n"
        f"👛 *Dompet:* `{DOMPET_ANDA[:6]}...{DOMPET_ANDA[-4:]}`\n"
        "🔔 Anda akan menerima pesan instan di sini setiap kali ada peluang atau cuan!"
    )
    
    last_block = 0
    loan_size = 2500.0 # Pinjaman Flash Loan $2.500
    last_telegram_time = 0
    
    while True:
        try:
            t0 = time.perf_counter()
            block, p_quick, p_uni = get_pure_onchain_data()
            latency_sec = time.perf_counter() - t0
            
            saldo_asli_pol = get_live_wallet_balance(DOMPET_ANDA)
            saldo_asli_idr = saldo_asli_pol * 1600
            
            if block > last_block and p_quick > 0 and p_uni > 0:
                last_block = block
                waktu = datetime.now().strftime("%H:%M:%S")
                
                selisih_murni_pct = (abs(p_quick - p_uni) / min(p_quick, p_uni)) * 100
                total_fee_pct = 0.44
                
                print(f"\n[BLOK #{block} | {waktu}] (Latency Node: {latency_sec:.4f}s)", flush=True)
                print(f"  ├─ 👛 SALDO ASLI DI DOMPET ANDA : {saldo_asli_pol:.6f} POL (Rp {saldo_asli_idr:,.0f})", flush=True)
                print(f"  ├─ Harga QuickSwap (Storage)   : ${p_quick:.8f}", flush=True)
                print(f"  ├─ Harga Uniswap V3 (Slot0)    : ${p_uni:.8f}", flush=True)
                print(f"  ├─ Selisih Nyata Saat Ini      : {selisih_murni_pct:.4f}% (Batas Minimal: {total_fee_pct}%)", flush=True)
                
                if selisih_murni_pct > total_fee_pct:
                    gross_usd = loan_size * (selisih_murni_pct / 100)
                    fee_usd = loan_size * (total_fee_pct / 100)
                    net_usd = gross_usd - fee_usd - 0.015
                    cuan_idr = net_usd * 16000
                    
                    print(f"  └─ 🟢 [PELUANG ASLI TERBUKA!] Selisih melebihi fee!", flush=True)
                    print(f"     🎉 Potensi Cuan Bersih: +${net_usd:.2f} (Rp {cuan_idr:,.0f})", flush=True)
                    
                    # Cegah spam: jeda minimal 60 detik antar alert jika spread berlanjut
                    current_epoch = time.time()
                    if current_epoch - last_telegram_time > 60:
                        last_telegram_time = current_epoch
                        msg = (
                            f"🎉 *PELUANG ARBITRASE CUAN TERDETEKSI!*\n\n"
                            f"⚡ *Blok:* `#{block}` | Jam: `{waktu}`\n"
                            f"📊 *Selisih Spread:* `{selisih_murni_pct:.3f}%`\n"
                            f"💰 *Estimasi Laba Bersih:* `+Rp {cuan_idr:,.0f} (+${net_usd:.2f})`\n"
                            f"👛 *Saldo Bensin:* `{saldo_asli_pol:.4f} POL`"
                        )
                        send_telegram_alert(msg)
                else:
                    kurang_pct = total_fee_pct - selisih_murni_pct
                    print(f"  └─ ⚪ [PASAR SEIMBANG] Selisih masih kurang {kurang_pct:.4f}% untuk untung.", flush=True)
                    print(f"     Bot tetap diam siaga. Saldo di dompet 100% aman tidak terpotong.", flush=True)
                
                print("-" * 80, flush=True)
            
            time.sleep(1.8)
            
        except Exception:
            # Jika ada gangguan koneksi sementara, otomatis lanjut sendiri tanpa berhenti
            time.sleep(3.0)

if __name__ == "__main__":
    main()
