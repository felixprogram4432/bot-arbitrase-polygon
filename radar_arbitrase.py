import time
import sys
import requests
from datetime import datetime
from collections import defaultdict

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Daftar token populer yang kita pantau
TOKENS = {
    "PEPE": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
    "SHIB": "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
}

def bersihkan_angka(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def cek_selisih_harga_pools(simbol, address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return []
        
        data = response.json()
        pairs = data.get("pairs", [])
        if not pairs:
            return []
        
        # Kelompokkan berdasarkan jaringan (chain)
        chain_pairs = defaultdict(list)
        for p in pairs:
            harga_usd = bersihkan_angka(p.get("priceUsd", 0))
            dex_nama = p.get("dexId", "unknown")
            network = p.get("chainId", "unknown")
            pair_addr = p.get("pairAddress", "")[:8]
            quote_token = p.get("quoteToken", {}).get("symbol", "USD")
            liquidity = bersihkan_angka(p.get("liquidity", {}).get("usd", 0))
            
            # Filter pool dengan likuiditas minimal $10.000
            if harga_usd > 0 and liquidity > 10000:
                label_pool = f"{dex_nama.upper()} ({quote_token} - pool:{pair_addr})"
                chain_pairs[network].append({
                    "pool_label": label_pool,
                    "network": network,
                    "price": harga_usd,
                    "liquidity": liquidity
                })
        
        hasil_peluang = []
        for network, pools in chain_pairs.items():
            if len(pools) >= 2:
                sorted_pools = sorted(pools, key=lambda x: x["price"])
                termurah = sorted_pools[0]
                termahal = sorted_pools[-1]
                
                # Cek jika ada selisih harga antar pool berbeda
                if termurah["price"] < termahal["price"]:
                    selisih_persen = ((termahal["price"] - termurah["price"]) / termurah["price"]) * 100
                    
                    # Simulasi Flash Loan $5.000
                    modal = 5000
                    gross_profit = modal * (selisih_persen / 100)
                    fee_aave = modal * 0.0009 # 0.09% fee
                    gas_fee = 0.50 if network != "ethereum" else 3.50
                    net_profit = gross_profit - fee_aave - gas_fee
                    
                    hasil_peluang.append({
                        "token": simbol,
                        "network": network.upper(),
                        "beli_di": termurah["pool_label"],
                        "harga_beli": termurah["price"],
                        "jual_di": termahal["pool_label"],
                        "harga_jual": termahal["price"],
                        "selisih_persen": selisih_persen,
                        "net_profit": net_profit
                    })
        return hasil_peluang
    except Exception as e:
        return []

def main():
    print("=" * 70, flush=True)
    print("   [*] RADAR ARBITRASE FLASH LOAN REAL-TIME DIAKTIFKAN [*]", flush=True)
    print("   Target Token: PEPE & SHIBA INU (Memantau Kolam Bursa)", flush=True)
    print("=" * 70, flush=True)
    
    scan_count = 0
    try:
        while True:
            scan_count += 1
            waktu = datetime.now().strftime("%H:%M:%S")
            print(f"\n[Scan #{scan_count} - Pukul {waktu}]", flush=True)
            
            for simbol, address in TOKENS.items():
                peluang_list = cek_selisih_harga_pools(simbol, address)
                for item in peluang_list:
                    print(f"\n[+] Token: {item['token']} (Jaringan: {item['network']})", flush=True)
                    print(f"   |-- Beli Murah di : {item['beli_di']} @ ${item['harga_beli']:.10f}", flush=True)
                    print(f"   |-- Jual Mahal di : {item['jual_di']} @ ${item['harga_jual']:.10f}", flush=True)
                    print(f"   |-- Selisih Harga : {item['selisih_persen']:.2f}%", flush=True)
                    
                    if item['net_profit'] > 0:
                        rp = item['net_profit'] * 16000
                        print(f"   \\-- [PELUANG CUAN!] Estimasi Profit Bersih Flash Loan ($5K): +${item['net_profit']:.2f} (Rp {rp:,.0f})", flush=True)
                    else:
                        print(f"   \\-- [BELUM CUAN] Estimasi Bersih setelah fee: ${item['net_profit']:.2f}", flush=True)
            
            print("-" * 70, flush=True)
            print("Scan ulang dalam 6 detik... (Tekan Ctrl+C untuk berhenti)", flush=True)
            time.sleep(6)
            
    except KeyboardInterrupt:
        print("\n\nRadar dimatikan.", flush=True)

if __name__ == "__main__":
    main()
