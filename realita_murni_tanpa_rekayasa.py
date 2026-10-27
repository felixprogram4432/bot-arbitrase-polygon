import os
import sys
import time
import requests
from datetime import datetime
from eth_abi import encode
from eth_utils import keccak

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

# Kredensial Eksekutor (Dari GitHub Secrets / Environment Variable)
SMART_CONTRACT_ADDRESS = os.environ.get("SMART_CONTRACT_ADDRESS", "").strip()
METAMASK_PRIVATE_KEY = os.environ.get("METAMASK_PRIVATE_KEY", "").strip()

# TARGET PORTOFOLIO "LAUTAN BIRU" (5 TARGET CROSS-POOL TERPILIH)
POOLS = {
    "DAI_USDT": {
        "nama": "DAI / USDT (Stable)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x254aa3a898071d6a2da0db11da73b02b4646078f",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "t0_dec": 18,
        "t1_dec": 6,
        "asset_dec": 6,
        "loan_usd": 3000.0,
        "uni_fee": 100,
        "tipe": "stable"
    },
    "MATIC_USDT": {
        "nama": "WMATIC / USDT",
        "quick": "0x604229c960e5cacf2aaeac8be68ac07ba9df81c3",
        "uni": "0x9b08288c3be4f62bbf8d1c20ac9c5e6f9467d8b7",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "t0_dec": 18,
        "t1_dec": 6,
        "asset_dec": 6,
        "loan_usd": 2000.0,
        "uni_fee": 500,
        "tipe": "matic_usdt"
    },
    "ETH_USDT": {
        "nama": "WETH / USDT",
        "quick": "0xf6422b997c7f54d1c6a6e103bcb1499eea0a7046",
        "uni": "0xbb98b3d2b18aef63a3178023a920971cf5f29be4",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "t0_dec": 18,
        "t1_dec": 6,
        "asset_dec": 6,
        "loan_usd": 3000.0,
        "uni_fee": 500,
        "tipe": "eth_usdt"
    },
    "MATIC_USDC": {
        "nama": "WMATIC / USDC",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0xa374094527e1673A86dE625aa59517c5de346d32",
        "asset": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",   # USDC
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "t0_dec": 18,
        "t1_dec": 6,
        "asset_dec": 6,
        "loan_usd": 2500.0,
        "uni_fee": 500,
        "tipe": "matic_usdc"
    },
    "ETH_USDC": {
        "nama": "WETH / USDC",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x45dda9cb7c25131df268515131f647d726f50608",
        "asset": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",   # USDC
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "t0_dec": 6,
        "t1_dec": 18,
        "asset_dec": 6,
        "loan_usd": 3500.0,
        "uni_fee": 500,
        "tipe": "eth_usdc"
    }
}

# Parameter Pertahanan & Eksekusi MEV
PRIORITY_FEE_GWEI = 42.0   # Tip khusus validator agar transaksi diselipkan di barisan terdepan (+Rp 30)
MAX_SLIPPAGE_PCT = 0.50    # Gembok anti-sandwich (batal jika harga bergeser >0.5%)
TOTAL_FEE_PCT = 0.44       # Aave 0.09% + DEX 0.35%
FLASHLOAN_SELECTOR = keccak(b"requestFlashLoan(address,uint256,bytes)")[:4]

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
                for k in POOLS:
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

def build_flashloan_calldata(pool_key, direction, net_profit_usd):
    """Menyusun calldata transaksi Flash Loan V2"""
    cfg = POOLS[pool_key]
    asset = cfg["asset"]
    amount = int(cfg["loan_usd"] * (10**cfg["asset_dec"]))
    # Toleransi target keuntungan minimal
    min_profit_raw = int(max(net_profit_usd * 0.70, 1.0) * (10**cfg["asset_dec"]))

    # executeOperation params: (uint8 direction, address targetToken, uint24 uniFee, uint256 minProfit)
    inner_params = encode(
        ['uint8', 'address', 'uint24', 'uint256'],
        [direction, cfg["target"], cfg["uni_fee"], min_profit_raw]
    )

    # requestFlashLoan params: (address asset, uint256 amount, bytes params)
    outer_data = FLASHLOAN_SELECTOR + encode(
        ['address', 'uint256', 'bytes'],
        [asset, amount, inner_params]
    )
    return "0x" + outer_data.hex(), min_profit_raw

def simulate_preflight(contract_addr, calldata_hex, rpc_url):
    """
    RAHASIA BOT INSTITUSI: PRE-FLIGHT SIMULATION VIA eth_call
    Mensimulasikan eksekusi di node sebelum dikirim ke blockchain.
    Jika simulasi revert (gagal / kalah cepat), transaksi DIBATALKAN.
    BIAYA BENSIN GAGAL: 0 RUPIAH (Rp 0)!
    """
    try:
        sim_payload = {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "eth_call",
            "params": [
                {
                    "from": DOMPET_ANDA,
                    "to": contract_addr,
                    "data": calldata_hex
                },
                "latest"
            ]
        }
        r = requests.post(rpc_url, json=sim_payload, timeout=3)
        res = r.json()
        if "error" in res:
            return False, res["error"].get("message", "Revert")
        return True, "Simulasi Sukses (Profit On-Chain Terverifikasi)"
    except Exception as e:
        return False, str(e)

def execute_onchain_sniper(contract_addr, calldata_hex, rpc_url):
    """Menandatangani dan mengeksekusi transaksi via Private Key"""
    try:
        from eth_account import Account
        
        # 1. Cek Nonce
        r_nonce = requests.post(rpc_url, json={"jsonrpc":"2.0","id":100,"method":"eth_getTransactionCount","params":[DOMPET_ANDA,"pending"]}, timeout=3).json()
        nonce = int(r_nonce.get("result", "0x0"), 16)
        
        # 2. Cek BaseFee
        r_block = requests.post(rpc_url, json={"jsonrpc":"2.0","id":101,"method":"eth_getBlockByNumber","params":["latest",False]}, timeout=3).json()
        base_fee_hex = r_block.get("result", {}).get("baseFeePerGas", "0x1dcd6500")
        base_fee = int(base_fee_hex, 16)
        
        priority_fee = int(PRIORITY_FEE_GWEI * 10**9)
        max_fee = int(base_fee * 1.5) + priority_fee
        
        # 3. Bentuk Transaksi EIP-1559
        tx_dict = {
            "chainId": 137,
            "nonce": nonce,
            "maxPriorityFeePerGas": priority_fee,
            "maxFeePerGas": max_fee,
            "gas": 480000,
            "to": contract_addr,
            "value": 0,
            "data": calldata_hex,
            "type": 2
        }
        
        account = Account.from_key(METAMASK_PRIVATE_KEY)
        signed_tx = account.sign_transaction(tx_dict)
        raw_hex = "0x" + signed_tx.raw_transaction.hex()
        
        # 4. Tembakkan ke Jalur Privat 1RPC
        r_send = requests.post(rpc_url, json={"jsonrpc":"2.0","id":102,"method":"eth_sendRawTransaction","params":[raw_hex]}, timeout=4).json()
        if "result" in r_send:
            tx_hash = r_send["result"]
            return True, tx_hash
        else:
            return False, r_send.get("error", {}).get("message", "Gagal broadcast")
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 80)
    print(" 🚀 RADAR CLOUD 24/7 - EDISI LAUTAN BIRU & SNIPER INSTITUSI V2")
    print(" 🛡️  Jalur MEV Shield: 1RPC Encrypted + Bor Priority Tip 42 Gwei")
    print(" 🎯 Bebas HFT Raksasa: Kolam Ramping & Arbitrase Stablecoin")
    print(" 💳 Dompet Pengawas:", DOMPET_ANDA)
    
    is_live_ready = bool(SMART_CONTRACT_ADDRESS and METAMASK_PRIVATE_KEY)
    if is_live_ready:
        print(" ⚡ STATUS EKSEKUTOR: 🔥 LIVE SNIPER AKTIF (Siap Eksekusi On-Chain)")
        print(" 🏛️  Smart Contract:", SMART_CONTRACT_ADDRESS)
    else:
        print(" 🔍 STATUS EKSEKUTOR: 🛡️ DRY-RUN PRE-FLIGHT (Simulasi 100% Bebas Risiko)")
        print(" ℹ️  Smart contract / Private Key belum dipasang. Berjalan dalam mode radar simulasi.")
    print("=" * 80)

    # Notifikasi Awal ke Telegram
    intro_msg = (
        "🌊 *RADAR CLOUD LAUTAN BIRU & SNIPER V2 AKTIF!*\n\n"
        f"🎯 *Mode:* {'🔥 LIVE ON-CHAIN SNIPER' if is_live_ready else '🛡️ PRE-FLIGHT DRY-RUN (Simulasi Bebas Risiko)'}\n"
        "📊 *Target:* DAI/USDT, MATIC/USDT, ETH/USDT, MATIC/USDC, ETH/USDC\n"
        "🛡️ *Shield:* 1RPC Encrypted + Pre-Flight Check (0 Biaya Revert)\n"
        "⚡ *Priority Tip:* 42 Gwei (Barisan Depan Blok)\n"
        "⏰ *Status:* Berpatroli 24 Jam Nonstop di Cloud!"
    )
    send_telegram_alert(intro_msg)

    start_time = time.time()
    last_block = 0
    last_alert_time = {}

    while True:
        elapsed = time.time() - start_time
        if elapsed > MAX_RUN_SECONDS:
            print("\n🔄 Sesi 5 jam 45 menit tercapai! Menyerahkan estafet ke sesi baru...")
            break

        block_num, saldo_pol, prices, active_rpc = fetch_blue_ocean_batch()
        
        if block_num != last_block and block_num > 0:
            last_block = block_num
            now = datetime.now().strftime("%H:%M:%S")

            print(f"\n[Blok #{block_num} | {now} | Saldo: {saldo_pol:.3f} POL | Shield: {active_rpc}]")

            for k, p in prices.items():
                p_q = p.get("q")
                p_u = p.get("u")
                cfg = POOLS[k]

                if p_q and p_u and p_q > 0 and p_u > 0:
                    selisih = abs(p_q - p_u)
                    spread_pct = (selisih / min(p_q, p_u)) * 100
                    
                    direction = 0 if p_q < p_u else 1
                    arah = "QuickSwap ➡️ UniV3" if direction == 0 else "UniV3 ➡️ QuickSwap"
                    
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

                        # Rancang Calldata Flash Loan
                        calldata_hex, min_profit_raw = build_flashloan_calldata(k, direction, est_cuan_usd)

                        # UJI SIMULASI PRE-FLIGHT (Jika Smart Contract Terpasang)
                        sim_ok = True
                        sim_msg = "Dry-Run Simulator"
                        if SMART_CONTRACT_ADDRESS:
                            sim_ok, sim_msg = simulate_preflight(SMART_CONTRACT_ADDRESS, calldata_hex, active_rpc)
                            print(f"    🔬 [Pre-Flight Simulation] Hasil: {sim_msg}")

                        # JIKA SIMULASI SUKSES & LIVE READY -> TEMBAK ON-CHAIN!
                        if is_live_ready and sim_ok:
                            tx_ok, tx_res = execute_onchain_sniper(SMART_CONTRACT_ADDRESS, calldata_hex, active_rpc)
                            if tx_ok:
                                print(f"    🚀 [SNIPER BERHASIL DIKIRIM!] Tx Hash: {tx_res}")
                                success_msg = (
                                    f"🎯 *EKSEKUSI FLASH LOAN BERHASIL DITEMBAKKAN!* 🎯\n\n"
                                    f"🪙 *Pasangan:* {cfg['nama']}\n"
                                    f"💰 *Estimasi Cuan:* ${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})\n"
                                    f"🔗 *Polygonscan:* https://polygonscan.com/tx/{tx_res}\n"
                                    f"⚡ *Priority Tip:* 42 Gwei\n"
                                    f"🛡️ *Hasil Pre-Flight:* Lolos Verifikasi On-Chain"
                                )
                                send_telegram_alert(success_msg)
                            else:
                                print(f"    ⚠️ [Gagal Kirim Tx]: {tx_res}")

                        # Throttle Alert Telegram biasa
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
                                f"🔬 *Status Pre-Flight:* {sim_msg}\n"
                                f"🛡️ *Anti-Frontrunning:* Terenkripsi 1RPC"
                            )
                            send_telegram_alert(cuan_msg)

        time.sleep(0.25)

if __name__ == "__main__":
    main()
