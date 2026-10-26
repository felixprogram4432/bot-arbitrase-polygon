import time
import sys
import os
import csv
import requests
from datetime import datetime

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Daftar Token Paling Likuid & Terpercaya di Polygon
TARGET_TOKENS = {
    "POL (Native WMATIC)": "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270",
    "WETH (Wrapped Ether)": "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619",
    "WBTC (Wrapped Bitcoin)": "0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6",
    "QUICK (QuickSwap)": "0xb5c064f955d8e7f38fe0460c556a72987494ee17",
    "LINK (Chainlink)": "0x53e0bca35ec356bd5dddfebbd1fc0fd03fabad39"
}

CSV_FILE = os.path.join(os.path.dirname(__file__), "arbitrase_polygon_history.csv")

def bersihkan_angka(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def inisialisasi_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Token", "Beli_DEX", "Harga_Beli_USD",
                "Jual_DEX", "Harga_Jual_USD", "Selisih_Pct",
                "Gross_Profit_USD", "Net_Profit_USD", "Net_Profit_IDR"
            ])

def catat_ke_csv(opp):
    try:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                opp["token"],
                opp["beli_di"],
                f"{opp['harga_beli']:.8f}",
                opp["jual_di"],
                f"{opp['harga_jual']:.8f}",
                f"{opp['selisih_pct']:.3f}%",
                f"${opp['gross_profit']:.2f}",
                f"${opp['net_profit']:.2f}",
                f"Rp {opp['net_profit'] * 16000:,.0f}"
            ])
    except Exception:
        pass

def scan_token_multidex(nama_token, token_address, loan_size_usd=2500.0):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return []
        
        pairs = r.json().get("pairs", [])
        polygon_pools = []
        for p in pairs:
            if p.get("chainId", "").lower() == "polygon":
                price = bersihkan_angka(p.get("priceUsd", 0))
                dex = p.get("dexId", "unknown").upper()
                quote = p.get("quoteToken", {}).get("symbol", "USD")
                liq = bersihkan_angka(p.get("liquidity", {}).get("usd", 0))

                # Hanya ambil kolam dengan likuiditas minimal $15.000 agar realistis
                if price > 0 and liq > 15000:
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
            
            # Filter anomali: selisih wajar arbitrase biasanya antara 0.4% sampai 8%
            if selisih_pct > 8.0:
                return []
                
            # Hitungan Biaya Realistis:
            # 1. Gross Profit dari pinjaman Flash Loan $2.500
            gross_profit = loan_size_usd * (selisih_pct / 100)
            
            # 2. Fee Pinjaman Aave V3 (0.09%)
            fee_aave = loan_size_usd * 0.0009
            
            # 3. Fee Swap Bursa (rata-rata 0.25% per swap x 2 = 0.5%)
            fee_swap_dex = loan_size_usd * 0.005
            
            # 4. Gas fee Polygon (Rp 250 / $0.015)
            gas_fee_polygon = 0.015
            
            # Net Profit Murni Bersih
            net_profit = gross_profit - fee_aave - fee_swap_dex - gas_fee_polygon
            
            # Hanya lolos jika benar-benar menghasilkan keuntungan bersih di atas $1.00
            if net_profit > 1.00:
                return [{
                    "token": nama_token,
                    "beli_di": termurah["dex_label"],
                    "harga_beli": termurah["price"],
                    "jual_di": termahal["dex_label"],
                    "harga_jual": termahal["price"],
                    "selisih_pct": selisih_pct,
                    "gross_profit": gross_profit,
                    "net_profit": net_profit
                }]
        return []
    except Exception:
        return []

def main():
    inisialisasi_csv()
    print("=" * 75, flush=True)
    print("   🚀 RADAR ARBITRASE POLYGON PRO (ULTRA-REALISTIC NET PROFIT) 🚀", flush=True)
    print("   Memantau Token Likuid di QuickSwap, Uniswap V3, SushiSwap, Balancer...", flush=True)
    print(f"   Simulasi Pinjaman Flash Loan : $2,500 USD (Aave V3 Polygon)", flush=True)
    print(f"   Pencatatan Otomatis Riwayat  : {os.path.basename(CSV_FILE)}", flush=True)
    print("=" * 75, flush=True)
    
    scan_count = 0
    total_peluang = 0
    total_potensi_cuan_usd = 0.0
    
    try:
        while True:
            scan_count += 1
            waktu = datetime.now().strftime("%H:%M:%S")
            print(f"\n[Scan #{scan_count} - Pukul {waktu}]", flush=True)
            
            ada_peluang_scan_ini = False
            for nama, addr in TARGET_TOKENS.items():
                peluang_list = scan_token_multidex(nama, addr, loan_size_usd=2500.0)
                for opp in peluang_list:
                    ada_peluang_scan_ini = True
                    total_peluang += 1
                    total_potensi_cuan_usd += opp["net_profit"]
                    
                    catat_ke_csv(opp)
                    
                    rp = opp["net_profit"] * 16000
                    print(f"\n⚡ [PELUANG CUAN DITEMUKAN!] Token: {opp['token']}", flush=True)
                    print(f"   |-- Beli Murah di : {opp['beli_di']} @ ${opp['harga_beli']:.6f}", flush=True)
                    print(f"   |-- Jual Mahal di : {opp['jual_di']} @ ${opp['harga_jual']:.6f}", flush=True)
                    print(f"   |-- Selisih Harga : {opp['selisih_pct']:.3f}%", flush=True)
                    print(f"   |-- Estimasi Bersih (Setelah Potong Semua Fee & Gas Rp 250):", flush=True)
                    print(f"   \\-- 🟢 NET PROFIT: +${opp['net_profit']:.2f} (Rp {rp:,.0f}) [Tersimpan di CSV!]", flush=True)
                
                time.sleep(0.4)
            
            if not ada_peluang_scan_ini:
                print("   -> Pasar sedang stabil seimbang, belum ada selisih yang melebihi fee...", flush=True)
            
            print("-" * 75, flush=True)
            print(f"📊 STATISTIK HARI INI: {total_peluang} Peluang | Total Akumulasi: ${total_potensi_cuan_usd:,.2f} (Rp {total_potensi_cuan_usd * 16000:,.0f})", flush=True)
            print("Scan berikutnya dalam 6 detik... (Tekan Ctrl+C untuk berhenti)", flush=True)
            time.sleep(6)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 75, flush=True)
        print("RADAR POLYGON PRO DIMATIKAN.", flush=True)
        print(f"Total Scan Dijalankan       : {scan_count} kali", flush=True)
        print(f"Total Peluang Terdokumentasi: {total_peluang} kali", flush=True)
        print(f"Total Potensi Keuntungan    : ${total_potensi_cuan_usd:,.2f} (Rp {total_potensi_cuan_usd * 16000:,.0f})", flush=True)
        print(f"Riwayat tersimpan di        : {CSV_FILE}", flush=True)
        print("=" * 75, flush=True)

if __name__ == "__main__":
    main()
