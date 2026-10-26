import time
import sys
import requests
from datetime import datetime
from collections import defaultdict

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Target token yang dipantau
TOKENS = {
    "PEPE": "0x6982508145454ce325ddbe47a25d4ec3d2311933",
    "SHIB": "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"
}

def bersihkan_angka(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

class SimulatorFlashLoan:
    def __init__(self, dompet_address="0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"):
        self.dompet_address = dompet_address
        self.saldo_profit_usd = 0.0
        self.total_transaksi = 0
        self.pinjaman_per_transaksi = 5000.0  # $5.000 Flash Loan
        self.fee_aave_rate = 0.0009           # 0.09% Aave V3 Fee
        self.gas_fee_l2 = 0.25                # Estimasi gas di L2/Polygon

    def fetch_live_pools(self, token_symbol, address):
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                return []
            
            pairs = r.json().get("pairs", [])
            chain_pools = defaultdict(list)
            for p in pairs:
                price = bersihkan_angka(p.get("priceUsd", 0))
                dex_nama = p.get("dexId", "unknown").upper()
                chain = p.get("chainId", "unknown").upper()
                pair_id = p.get("pairAddress", "")[:8]
                quote = p.get("quoteToken", {}).get("symbol", "USD")
                liq = bersihkan_angka(p.get("liquidity", {}).get("usd", 0))

                if price > 0 and liq > 5000:
                    chain_pools[chain].append({
                        "dex": f"{dex_nama} ({quote}-{pair_id})",
                        "price": price,
                        "chain": chain
                    })
            
            peluang = []
            for chain, pools in chain_pools.items():
                if len(pools) >= 2:
                    sorted_pools = sorted(pools, key=lambda x: x["price"])
                    termurah = sorted_pools[0]
                    termahal = sorted_pools[-1]
                    
                    if termahal["price"] > termurah["price"]:
                        selisih_pct = ((termahal["price"] - termurah["price"]) / termurah["price"]) * 100
                        gross = self.pinjaman_per_transaksi * (selisih_pct / 100)
                        fee_aave = self.pinjaman_per_transaksi * self.fee_aave_rate
                        net = gross - fee_aave - self.gas_fee_l2
                        
                        peluang.append({
                            "token": token_symbol,
                            "chain": chain,
                            "beli_dex": termurah["dex"],
                            "beli_price": termurah["price"],
                            "jual_dex": termahal["dex"],
                            "jual_price": termahal["price"],
                            "selisih_pct": selisih_pct,
                            "gross_profit": gross,
                            "fee_aave": fee_aave,
                            "net_profit": net
                        })
            return peluang
        except Exception:
            return []

    def eksekusi_flash_loan(self, opp):
        self.total_transaksi += 1
        print("\n" + "=" * 65, flush=True)
        print(f"⚡ [TRIGGER DETEKSI] Peluang Arbitrase Ditemukan di {opp['token']}!", flush=True)
        print("=" * 65, flush=True)
        print(f"Jaringan         : {opp['chain']}", flush=True)
        print(f"Bursa Beli Murah : {opp['beli_dex']} -> ${opp['beli_price']:.10f}", flush=True)
        print(f"Bursa Jual Mahal : {opp['jual_dex']} -> ${opp['jual_price']:.10f}", flush=True)
        print(f"Selisih Harga    : {opp['selisih_pct']:.2f}%", flush=True)
        print("-" * 65, flush=True)
        print("Memulai Alur Eksekusi Smart Contract (Flash Loan 1 Blok):", flush=True)
        
        # Langkah 1
        time.sleep(0.8)
        print(f"  [1/5] Meminjam ${self.pinjaman_per_transaksi:,.2f} dari Kolam Aave V3... [BERHASIL]", flush=True)
        
        # Langkah 2
        time.sleep(0.8)
        tokens_bought = self.pinjaman_per_transaksi / opp["beli_price"]
        print(f"  [2/5] Beli {tokens_bought:,.0f} {opp['token']} di {opp['beli_dex']}... [BERHASIL]", flush=True)
        
        # Langkah 3
        time.sleep(0.8)
        revenue = tokens_bought * opp["jual_price"]
        print(f"  [3/5] Jual ke {opp['jual_dex']} menghasilkan ${revenue:,.2f}... [BERHASIL]", flush=True)
        
        # Langkah 4
        time.sleep(0.8)
        total_repay = self.pinjaman_per_transaksi + opp["fee_aave"]
        print(f"  [4/5] Mengembalikan pinjaman ke Aave (${total_repay:,.2f})... [LUNAS]", flush=True)
        
        # Langkah 5
        time.sleep(0.8)
        self.saldo_profit_usd += opp["net_profit"]
        rp = opp["net_profit"] * 16000
        print(f"  [5/5] Gas fee terbayar (-${self.gas_fee_l2:.2f}). Mengirim sisa untung...", flush=True)
        print("-" * 65, flush=True)
        print(f"🎉 SUKSES! Profit Bersih: +${opp['net_profit']:.2f} (Rp {rp:,.0f})", flush=True)
        print(f"   Tujuan Transfer: {self.dompet_address}", flush=True)
        print(f"   Total Saldo Terkumpul Saat Ini: ${self.saldo_profit_usd:,.2f} (Rp {self.saldo_profit_usd * 16000:,.0f})", flush=True)
        print("=" * 65 + "\n", flush=True)

def main():
    print("=" * 70, flush=True)
    print("      🚀 SIMULATOR RESMI FLASH LOAN DEFI (ARBITRASE REAL-TIME) 🚀", flush=True)
    print("=" * 70, flush=True)
    print("Dompet Penerima : 0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36", flush=True)
    print("Modal Pinjaman  : $5,000 USD (Aave V3 No-Collateral)", flush=True)
    print("Status          : Siap mendengarkan pasar live...", flush=True)
    print("=" * 70, flush=True)

    sim = SimulatorFlashLoan()
    iterasi = 0
    try:
        while True:
            iterasi += 1
            waktu = datetime.now().strftime("%H:%M:%S")
            print(f"[{waktu}] Scanning harga PEPE & SHIB di berbagai bursa... (Scan #{iterasi})", flush=True)
            
            peluang_ditemukan = False
            for token_sym, addr in TOKENS.items():
                peluang_list = sim.fetch_live_pools(token_sym, addr)
                for opp in peluang_list:
                    # Jika ada selisih yang menghasilkan profit di atas $1
                    if opp["net_profit"] > 1.0:
                        peluang_ditemukan = True
                        sim.eksekusi_flash_loan(opp)
                        break
                if peluang_ditemukan:
                    break
            
            if not peluang_ditemukan:
                print("   -> Belum ada selisih yang cukup menguntungkan saat ini.", flush=True)

            print("Menunggu 7 detik untuk scan berikutnya... (Tekan Ctrl+C untuk stop)\n", flush=True)
            time.sleep(7)

    except KeyboardInterrupt:
        print("\n" + "=" * 65, flush=True)
        print("SIMULASI SELESAI!", flush=True)
        print(f"Total Transaksi Berhasil : {sim.total_transaksi} kali", flush=True)
        print(f"Total Keuntungan Masuk   : ${sim.saldo_profit_usd:,.2f} (Rp {sim.saldo_profit_usd * 16000:,.0f})", flush=True)
        print("=" * 65, flush=True)

if __name__ == "__main__":
    main()
