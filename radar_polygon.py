import time
import sys
import requests
from datetime import datetime
from collections import defaultdict

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Token Likuid di Jaringan Polygon (PoS)
POLYGON_TOKENS = {
    "WMATIC (POL)": "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270",
    "WETH (Polygon)": "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619",
    "USDC (Polygon)": "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",
    "WBTC (Polygon)": "0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6"
}

def bersihkan_angka(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def scan_polygon_pools(token_nama, contract_addr):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_addr}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return []
        
        pairs = r.json().get("pairs", [])
        polygon_pools = []
        for p in pairs:
            chain = p.get("chainId", "").lower()
            if chain == "polygon":
                price = bersihkan_angka(p.get("priceUsd", 0))
                dex = p.get("dexId", "unknown").upper()
                pair_id = p.get("pairAddress", "")[:8]
                quote = p.get("quoteToken", {}).get("symbol", "USD")
                liq = bersihkan_angka(p.get("liquidity", {}).get("usd", 0))

                # Hanya ambil pool yang likuiditasnya > $10.000 agar realistis
                if price > 0 and liq > 10000:
                    polygon_pools.append({
                        "dex_label": f"{dex} ({quote})",
                        "price": price,
                        "liquidity": liq
                    })
        
        if len(polygon_pools) < 2:
            return []
        
        sorted_pools = sorted(polygon_pools, key=lambda x: x["price"])
        termurah = sorted_pools[0]
        termahal = sorted_pools[-1]
        
        if termahal["price"] > termurah["price"]:
            selisih_pct = ((termahal["price"] - termurah["price"]) / termurah["price"]) * 100
            
            # Simulasi Flash Loan $2.000 di Polygon
            modal = 2000.0
            gross_profit = modal * (selisih_pct / 100)
            fee_aave = modal * 0.0009 # 0.09% fee
            gas_fee_polygon = 0.02    # Gas fee Polygon cuma ~$0.02 (Rp 300!)
            net_profit = gross_profit - fee_aave - gas_fee_polygon
            
            return [{
                "token": token_nama,
                "beli_di": termurah["dex_label"],
                "harga_beli": termurah["price"],
                "jual_di": termahal["dex_label"],
                "harga_jual": termahal["price"],
                "selisih_pct": selisih_pct,
                "net_profit": net_profit
            }]
        return []
    except Exception:
        return []

def main():
    print("=" * 70, flush=True)
    print("   🌐 RADAR ARBITRASE RESMI JARINGAN POLYGON (BIAYA GAS Rp 300) 🌐", flush=True)
    print("   Memantau Bursa Polygon: QuickSwap, Uniswap V3, SushiSwap...", flush=True)
    print("=" * 70, flush=True)
    
    scan_idx = 0
    try:
        while True:
            scan_idx += 1
            waktu = datetime.now().strftime("%H:%M:%S")
            print(f"\n[Scan Polygon #{scan_idx} - Pukul {waktu}]", flush=True)
            
            ada_peluang = False
            for nama, addr in POLYGON_TOKENS.items():
                peluang = scan_polygon_pools(nama, addr)
                for item in peluang:
                    ada_peluang = True
                    print(f"\n[+] Token: {item['token']}", flush=True)
                    print(f"   |-- Beli Murah di : {item['beli_di']} @ ${item['harga_beli']:.6f}", flush=True)
                    print(f"   |-- Jual Mahal di : {item['jual_di']} @ ${item['harga_jual']:.6f}", flush=True)
                    print(f"   |-- Selisih Harga : {item['selisih_pct']:.3f}%", flush=True)
                    
                    rp = item['net_profit'] * 16000
                    if item['net_profit'] > 0:
                        print(f"   \\-- 🟢 [CUAN POLYGON] Estimasi Profit Bersih Flash Loan ($2K): +${item['net_profit']:.2f} (Rp {rp:,.0f})", flush=True)
                    else:
                        print(f"   \\-- ⚪ [BELUM CUAN] Estimasi Bersih: ${item['net_profit']:.2f}", flush=True)
            
            if not ada_peluang:
                print("   Belum ada perbedaan harga antar-bursa di Polygon saat ini...", flush=True)
                
            print("-" * 70, flush=True)
            print("Scan ulang dalam 6 detik... (Tekan Ctrl+C untuk berhenti)", flush=True)
            time.sleep(6)
            
    except KeyboardInterrupt:
        print("\nRadar Polygon dimatikan.", flush=True)

if __name__ == "__main__":
    main()
