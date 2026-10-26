import time
import sys
import requests
from datetime import datetime

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"

# Alamat Dompet Resmi Anda
DOMPET_ANDA = "0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"

# Kolam Likuiditas Nyata Polygon
POOLS = {
    "QuickSwap": "0x6e7a5FAFcec6BB1e78bAE2A1F0B612012BF14827",
    "UniswapV3": "0xA374094527e1673A86dE625aa59517c5dE346d32"
}

def get_live_wallet_balance(wallet_address):
    # Membaca saldo koin POL asli di dompet langsung dari blockchain
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
        
        # Raw QuickSwap
        q_data = res[1].get("result", "")
        r0 = int(q_data[2:66], 16)
        r1 = int(q_data[66:130], 16)
        p_quick = (r1 / 10**6) / (r0 / 10**18)
        
        # Raw UniV3
        u_data = res[2].get("result", "")
        sqrtPriceX96 = int(u_data[2:66], 16)
        p_uni = ((sqrtPriceX96 / (2**96)) ** 2) * (10**12)
        
        return block, p_quick, p_uni
    except Exception:
        return 0, 0, 0

def main():
    print("=" * 80, flush=True)
    print("      🎯 RADAR REALITA MURNI + LIVE BALANCE TRACKER ON-CHAIN 🎯", flush=True)
    print(f"   Alamat Dompet : {DOMPET_ANDA}", flush=True)
    print("   Data Sumber   : Memori Smart Contract Polygon Asli (Block-by-Block)", flush=True)
    print("   Pasangan      : WMATIC / USDC (QuickSwap V2 vs Uniswap V3)", flush=True)
    print("   Syarat Cuan   : Selisih pasar nyata WAJIB > 0.44% untuk menghasilkan untung!", flush=True)
    print("=" * 80, flush=True)
    
    last_block = 0
    loan_size = 2500.0 # Pinjaman Flash Loan $2.500
    
    try:
        while True:
            t0 = time.perf_counter()
            block, p_quick, p_uni = get_pure_onchain_data()
            latency_sec = time.perf_counter() - t0
            
            # Baca saldo koin POL asli di dompet detik ini
            saldo_asli_pol = get_live_wallet_balance(DOMPET_ANDA)
            saldo_asli_idr = saldo_asli_pol * 1600 # Kurs ~Rp 1.600 per POL
            
            if block > last_block and p_quick > 0 and p_uni > 0:
                last_block = block
                waktu = datetime.now().strftime("%H:%M:%S")
                
                # SELISIH MURNI 100% DARI PASAR (NOL REKAYASA!)
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
                else:
                    kurang_pct = total_fee_pct - selisih_murni_pct
                    print(f"  └─ ⚪ [PASAR SEIMBANG] Selisih masih kurang {kurang_pct:.4f}% untuk untung.", flush=True)
                    print(f"     Bot tetap diam siaga. Saldo di dompet 100% aman tidak terpotong.", flush=True)
                
                print("-" * 80, flush=True)
            
            time.sleep(1.8)
            
    except KeyboardInterrupt:
        print("\nRadar Murni dimatikan.", flush=True)

if __name__ == "__main__":
    main()
