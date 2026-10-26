import time
import sys
import os
import requests
from datetime import datetime

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Node RPC Resmi Polygon Berkecepatan Tinggi (Koneksi Langsung ke Mesin Bor)
POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"

# Alamat Kolam Penyimpanan Likuiditas di Polygon
POOLS = {
    "QuickSwap_WMATIC_USDC": {
        "address": "0x6e7a5FAFcec6BB1e78bAE2A1F0B612012BF14827",
        "type": "v2",
        "dex": "QuickSwap",
        "token0_dec": 18,
        "token1_dec": 6
    },
    "UniswapV3_WMATIC_USDC": {
        "address": "0xA374094527e1673A86dE625aa59517c5dE346d32",
        "type": "v3",
        "dex": "Uniswap V3",
        "token0_dec": 18,
        "token1_dec": 6
    }
}

def get_onchain_price_quickswap(pair_address):
    # Selector bytecode 'getReserves()' adalah 0x0902f1ac
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": pair_address, "data": "0x0902f1ac"}, "latest"],
        "id": 1
    }
    t0 = time.time()
    r = requests.post(POLYGON_RPC, json=payload, timeout=3)
    latency_ms = (time.time() - t0) * 1000
    
    data = r.json().get("result", "")
    if len(data) >= 130:
        r0 = int(data[2:66], 16)
        r1 = int(data[66:130], 16)
        # Harga WMATIC dalam USDC
        price = (r1 / 10**6) / (r0 / 10**18)
        return price, latency_ms
    return None, latency_ms

def get_onchain_price_uniswap_v3(pool_address):
    # Selector bytecode 'slot0()' adalah 0x3850c7bd
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": pool_address, "data": "0x3850c7bd"}, "latest"],
        "id": 2
    }
    t0 = time.time()
    r = requests.post(POLYGON_RPC, json=payload, timeout=3)
    latency_ms = (time.time() - t0) * 1000
    
    data = r.json().get("result", "")
    if len(data) >= 66:
        sqrtPriceX96 = int(data[2:66], 16)
        # Formula matematis Uniswap V3: price = (sqrtPriceX96 / 2^96)^2 * 10^(18-6)
        price = ((sqrtPriceX96 / (2**96)) ** 2) * (10**12)
        return price, latency_ms
    return None, latency_ms

def get_latest_block():
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 99}
    try:
        r = requests.post(POLYGON_RPC, json=payload, timeout=2)
        return int(r.json().get("result", "0"), 16)
    except Exception:
        return 0

def main():
    print("=" * 75, flush=True)
    print("   ⚡ ENGINE ARBITRASE KILAT (KONEKSI LANGSUNG KE STORAGE BLOCKCHAIN) ⚡", flush=True)
    print("   Mode      : Direct On-Chain RPC (Nol Perantara API / Sub-Detik)", flush=True)
    print("   Jaringan  : Polygon PoS (Bor Validator Node)", flush=True)
    print("   Target    : QuickSwap V2 vs Uniswap V3 (WMATIC / USDC)", flush=True)
    print("=" * 75, flush=True)
    
    last_block = 0
    tick_count = 0
    loan_size = 5000.0 # Simulasi Flash Loan $5.000
    
    try:
        while True:
            current_block = get_latest_block()
            
            # Setiap ada blok baru di Polygon (~2.1 detik per blok)
            if current_block > last_block:
                last_block = current_block
                tick_count += 1
                waktu = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # Baca harga langsung dari storage memori smart contract
                price_quick, lat_quick = get_onchain_price_quickswap(POOLS["QuickSwap_WMATIC_USDC"]["address"])
                price_uni, lat_uni = get_onchain_price_uniswap_v3(POOLS["UniswapV3_WMATIC_USDC"]["address"])
                
                if price_quick and price_uni:
                    selisih = abs(price_quick - price_uni)
                    selisih_pct = (selisih / min(price_quick, price_uni)) * 100
                    
                    print(f"\n[BLOK #{current_block} | {waktu}] (Latency: {lat_quick:.0f}ms / {lat_uni:.0f}ms)", flush=True)
                    print(f"   ├─ QuickSwap On-Chain : ${price_quick:.8f}", flush=True)
                    print(f"   ├─ Uniswap V3 Storage : ${price_uni:.8f}", flush=True)
                    print(f"   ├─ Selisih Real-Time  : {selisih_pct:.4f}%", flush=True)
                    
                    # Hitung profit kotor & bersih
                    gross_profit = loan_size * (selisih_pct / 100)
                    fee_total = (loan_size * 0.0019) + 0.015 # Fee Aave (0.09%) + V3 fee (0.10%) + Gas
                    net_profit = gross_profit - fee_total
                    
                    if net_profit > 0.50:
                        rp = net_profit * 16000
                        arah = "Beli di UniV3 -> Jual di Quick" if price_uni < price_quick else "Beli di Quick -> Jual di UniV3"
                        print(f"   └─ 🟢 [SINYAL TEMBAK!] {arah}", flush=True)
                        print(f"      Net Cuan Flash Loan ($5K): +${net_profit:.2f} (Rp {rp:,.0f}) [Ready to Broadcast!]", flush=True)
                    else:
                        print(f"   └─ ⚪ [MENUNGGU SPREAD] Margin saat ini belum melewati fee: ${net_profit:.2f}", flush=True)
            
            # Istirahat 0.8 detik untuk menyinkronkan dengan blok Polygon
            time.sleep(0.8)
            
    except KeyboardInterrupt:
        print("\n\nEngine Kilat dimatikan.", flush=True)

if __name__ == "__main__":
    main()
