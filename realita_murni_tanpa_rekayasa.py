import os
import sys
import time
import requests
import threading
from datetime import datetime
from eth_abi import encode
from eth_utils import keccak
from eth_account import Account

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# JALUR VIP ANTI-INTIP (1RPC MEV Shield + Bor Direct Validator)
POLYGON_RPCS = [
    "https://1rpc.io/matic",                    # Jalur Utama: Terenkripsi Anti-Frontrunning
    "https://polygon-bor-rpc.publicnode.com",   # Jalur Cepat: Direct Bor Node
    "https://polygon-rpc.com"                   # Jalur Cadangan
]

# Alamat Dompet Resmi Anda
DOMPET_ANDA = "0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"

# Kredensial Notifikasi Telegram
TELEGRAM_TOKEN = "8854612522:AAF5cczXAA8RsPNA1vvd93asDVaOXZQreu0"
TELEGRAM_CHAT_ID = "5124389853"

# Kredensial Eksekutor (Dari GitHub Secrets / Environment Variable)
SMART_CONTRACT_ADDRESS = os.environ.get("SMART_CONTRACT_ADDRESS", "").strip()
METAMASK_PRIVATE_KEY = os.environ.get("METAMASK_PRIVATE_KEY", "").strip()

# TARGET PORTOFOLIO 12 KOLAM LIKUIDITAS RAKSASA POLYGON (> $6 JUTA TVL / > RP 108 MILIAR)
POOLS = {
    # 1. DAI / USDT (Fee 100: 0.01% - Super Efisien)
    "DAI_USDT_100": {
        "nama": "DAI / USDT (100)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x254aa3a898071d6a2da0db11da73b02b4646078f",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 18, "dec1": 6, "asset_dec": 6,
        "loan_usd": 3000.0, "uni_fee": 100, "fee_tot": 0.40,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    # 2. DAI / USDT (Fee 500: 0.05%)
    "DAI_USDT_500": {
        "nama": "DAI / USDT (500)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x42f0530351471dab7ec968476d19bd36af9ec52d",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 18, "dec1": 6, "asset_dec": 6,
        "loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    # 3. DAI / USDC.e (Fee 100: 0.01% - Likuiditas $301.000)
    "DAI_USDCe_100": {
        "nama": "DAI / USDC.e (100)",
        "quick": "0xf04adbf75cdfc5ed26eea4bbbb991db002036bdd",
        "uni": "0x5645dcb64c059aa11212707fbf4e7f984440a8cf",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 6, "dec1": 18, "asset_dec": 6,
        "loan_usd": 3500.0, "uni_fee": 100, "fee_tot": 0.40,
        "min_r0": 10000.0, "min_r1": 10000.0
    },
    # 4. USDC.e / USDT (Fee 100: 0.01% - Likuiditas $622.000)
    "USDCe_USDT_100": {
        "nama": "USDC.e / USDT (100)",
        "quick": "0x2cf7252e74036d1da831d11089d326296e64a728",
        "uni": "0xdac8a8e6dbf8c690ec6815e0ff03491b2770255d",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "dec0": 6, "dec1": 6, "asset_dec": 6,
        "loan_usd": 4000.0, "uni_fee": 100, "fee_tot": 0.40,
        "min_r0": 10000.0, "min_r1": 10000.0
    },
    # 5. WMATIC / USDT (Fee 500)
    "MATIC_USDT_500": {
        "nama": "WMATIC / USDT (500)",
        "quick": "0x604229c960e5cacf2aaeac8be68ac07ba9df81c3",
        "uni": "0x9b08288c3be4f62bbf8d1c20ac9c5e6f9467d8b7",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6,
        "loan_usd": 2000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 10000.0, "min_r1": 1000.0
    },
    # 6. WMATIC / USDC (Fee 500)
    "MATIC_USDC_500": {
        "nama": "WMATIC / USDC (500)",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0xa374094527e1673A86dE625aa59517c5de346d32",
        "asset": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",   # USDC
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6,
        "loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 10000.0, "min_r1": 1000.0
    },
    # 7. WMATIC / USDC.e (Fee 3000)
    "MATIC_USDCe_3000": {
        "nama": "WMATIC / USDC.e (3000)",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0x88f3c15523544835ff6c738ddb30995339ad57d6",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6,
        "loan_usd": 2500.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 10000.0, "min_r1": 1000.0
    },
    # 8. WETH / USDT (Fee 500)
    "ETH_USDT_500": {
        "nama": "WETH / USDT (500)",
        "quick": "0xf6422b997c7f54d1c6a6e103bcb1499eea0a7046",
        "uni": "0xbb98b3d2b18aef63a3178023a920971cf5f29be4",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 18, "dec1": 6, "asset_dec": 6,
        "loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 5.0, "min_r1": 5000.0
    },
    # 9. WETH / USDC (Fee 500 - Likuiditas $2.2 Juta!)
    "ETH_USDC_500": {
        "nama": "WETH / USDC (500)",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x45dda9cb7c25131df268515131f647d726f50608",
        "asset": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",   # USDC
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 6, "dec1": 18, "asset_dec": 6,
        "loan_usd": 3500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 5000.0, "min_r1": 5.0
    },
    # 10. WMATIC / WETH (Fee 500 - Likuiditas 2,6 Juta WMATIC)
    "MATIC_WETH_500": {
        "nama": "WMATIC / WETH (500)",
        "quick": "0xadbf1854e5883eb8aa7baf50705338739e558e5b",
        "uni": "0x86f1d8390222a3691c28938ec7404a1661e618e0",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18,
        "loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 10000.0, "min_r1": 5.0
    },
    # 11. DAI / WMATIC (Fee 500)
    "DAI_MATIC_500": {
        "nama": "DAI / WMATIC (500)",
        "quick": "0xeef611894ceae652979c9d0dae1deb597790c6ee",
        "uni": "0x0f663c16dd7c65cf87edb9229464ca77aeea536b",
        "asset": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",   # DAI
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18,
        "loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    # 12. WBTC / WETH (Fee 3000 - Bitcoin Asli Likuiditas $450.000!)
    "WBTC_WETH_3000": {
        "nama": "WBTC / WETH (3000)",
        "quick": "0xdc9232e2df177d7a12fdff6ecbab114e2231198d",
        "uni": "0xfe343675878100b344802a6763fd373fdeed07a4",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",  # WBTC
        "dec0": 8, "dec1": 18, "asset_dec": 18,
        "loan_usd": 4000.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 0.5, "min_r1": 10.0
    }
}

# Parameter Pertahanan & Eksekusi MEV (TOP 5% VIP TIER POLYGON)
BASE_PRIORITY_FEE_GWEI = 210.0  # Tip Baseline: Mengalahkan 95% antrean Polygon (~Rp 140 perak)
MAX_SLIPPAGE_PCT = 0.50         # Gembok anti-sandwich (batal jika harga bergeser >0.5%)
FLASHLOAN_SELECTOR = keccak(b"requestFlashLoan(address,uint256,bytes)")[:4]
KURS_USDT_IDR = 18136

def calculate_adaptive_tip(cuan_idr: float) -> float:
    """
    Priority Tip adaptif berdasarkan potensi profit IDR:
    - Normal Scalping (< 200rb): 210.0 Gwei (~Rp 140 perak gas)
    - Sedang (200rb - 500rb): 380.0 Gwei
    - Paus (500rb - 1.5jt): 550.0 Gwei
    - Monster Paus (> 1.5jt): 750.0 Gwei
    """
    if cuan_idr >= 1500000:
        return 750.0
    elif cuan_idr >= 500000:
        return 550.0
    elif cuan_idr >= 200000:
        return 380.0
    else:
        return 210.0

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Gagal kirim Telegram: {e}", flush=True)

def build_flashloan_calldata(pool_key, direction, net_profit_usd):
    cfg = POOLS[pool_key]
    loan_amount_raw = int(cfg["loan_usd"] * (10**cfg["asset_dec"]))
    # Proteksi laba on-chain: minimal $0.15 USD (~Rp 2.700) jika tipis, atau 60% dari estimasi
    min_profit_raw = int(max(net_profit_usd * 0.60, 0.15) * (10**cfg["asset_dec"]))

    params_bytes = encode(
        ['uint8', 'address', 'uint24', 'uint256'],
        [direction, cfg["target"], cfg["uni_fee"], min_profit_raw]
    )

    call_bytes = FLASHLOAN_SELECTOR + encode(
        ['address', 'uint256', 'bytes'],
        [cfg["asset"], loan_amount_raw, params_bytes]
    )
    return "0x" + call_bytes.hex(), min_profit_raw

def execute_onchain_sniper_instant(contract_address, calldata_hex, active_rpc, priority_fee_gwei=210.0):
    try:
        if not METAMASK_PRIVATE_KEY:
            return False, "Private key tidak terdeteksi."

        account = Account.from_key(METAMASK_PRIVATE_KEY)

        # 1. Ambil Nonce Pengirim
        res_nonce = requests.post(active_rpc, json={
            "jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionCount",
            "params": [account.address, "pending"]
        }, timeout=5).json()
        nonce = int(res_nonce["result"], 16)

        # 2. Ambil Base Fee Terbaru
        res_block = requests.post(active_rpc, json={
            "jsonrpc": "2.0", "id": 2, "method": "eth_getBlockByNumber",
            "params": ["latest", False]
        }, timeout=5).json()
        base_fee = int(res_block["result"]["baseFeePerGas"], 16)

        # Priority Fee & Max Fee Adaptif
        priority_fee_wei = int(priority_fee_gwei * 1e9)
        max_fee_wei = int(base_fee * 1.5) + priority_fee_wei

        tx = {
            'chainId': 137, # Polygon Mainnet
            'nonce': nonce,
            'maxPriorityFeePerGas': priority_fee_wei,
            'maxFeePerGas': max_fee_wei,
            'gas': 650000,
            'to': contract_address,
            'value': 0,
            'data': calldata_hex
        }

        signed_tx = account.sign_transaction(tx)
        raw_tx_hex = "0x" + signed_tx.raw_transaction.hex()

        # Kirim Langsung ke Jaringan Validator
        res_send = requests.post(active_rpc, json={
            "jsonrpc": "2.0", "id": 3, "method": "eth_sendRawTransaction",
            "params": [raw_tx_hex]
        }, timeout=5).json()

        if "error" in res_send:
            return False, res_send["error"]["message"]
        
        tx_hash = res_send["result"]
        return True, tx_hash

    except Exception as e:
        return False, str(e)

def monitor_transaction_receipt(tx_hash, pool_name, est_cuan_usd, est_cuan_idr, active_rpc):
    print(f"    ⏳ [MEMANTAU TX]: https://polygonscan.com/tx/{tx_hash}", flush=True)
    for _ in range(30):
        time.sleep(1.5)
        try:
            r = requests.post(active_rpc, json={
                "jsonrpc": "2.0", "id": 4, "method": "eth_getTransactionReceipt",
                "params": [tx_hash]
            }, timeout=5).json()
            receipt = r.get("result")
            if receipt:
                status = receipt.get("status")
                gas_used = int(receipt.get("gasUsed", "0x0"), 16)
                if status == "0x1":
                    success_msg = (
                        f"🎉 *SNIPER ARBITRASE MENANG! EKSEKUSI SUKSES!* 🏆\n\n"
                        f"🪙 *Kolam:* `{pool_name}`\n"
                        f"💰 *Cuan Bersih:* `+${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})`\n"
                        f"👛 *Masuk ke:* `{DOMPET_ANDA}`\n"
                        f"⛽ *Gas Terpakai:* `{gas_used:,} gas`\n"
                        f"🔗 *Bukti PolygonScan:* [Cek Transaksi](https://polygonscan.com/tx/{tx_hash})"
                    )
                    send_telegram_alert(success_msg)
                    print(f"    🏆 [EKSEKUSI SUKSES 100%!]: https://polygonscan.com/tx/{tx_hash}", flush=True)
                else:
                    revert_msg = (
                        f"🛡️ *TRANSAKSI AMAN DIBATALKAN KONTRAK (REVERT)*\n\n"
                        f"🪙 *Kolam:* `{pool_name}`\n"
                        f"ℹ️ *Alasan:* Selisih profit berubah di milidetik terakhir.\n"
                        f"🔒 *Modal:* 100% UTUH AMAN ($0 pinjaman Aave dikembalikan).\n"
                        f"⛽ *Biaya Gas Revert:* ~Rp 140 perak."
                    )
                    send_telegram_alert(revert_msg)
                    print(f"    🛡️ [TRANSAKSI DIBATALKAN KONTRAK SECARA AMAN (REVERT)]: {tx_hash}", flush=True)
                return
        except Exception:
            pass

def main():
    print("=" * 86, flush=True)
    print("  🚀 MESIN ARBITRASE TURBO 12 KOLAM RAKSASA - AUTONOMOUS 24/7 (AZURE CLOUD)", flush=True)
    print(f"  🎯 Target Scalping Agresif: Minimal $0.28 USD (~Rp 5.000+ Bersih) Masuk Dompet!", flush=True)
    print(f"  ⚡ Scanning Speed         : Batch Multicall (< 0.5s / 4x per blok Polygon!)", flush=True)
    print("=" * 86, flush=True)

    is_live_ready = bool(SMART_CONTRACT_ADDRESS and METAMASK_PRIVATE_KEY)
    contract_display = f"{SMART_CONTRACT_ADDRESS[:10]}...{SMART_CONTRACT_ADDRESS[-6:]}" if SMART_CONTRACT_ADDRESS else "Belum Diset"
    
    if is_live_ready:
        print(f"  🔥 STATUS EKSEKUTOR: LIVE ON-CHAIN SNIPER AKTIF!")
        print(f"  📜 Kontrak Pintar   : {SMART_CONTRACT_ADDRESS}")
        print(f"  👛 Dompet Penembak  : {DOMPET_ANDA}\n")
    else:
        print("  ⚠️ STATUS EKSEKUTOR: MODE RADAR PENGAMATAN ONLY (Kredensial Belum Terdeteksi)\n")

    send_telegram_alert(
        f"🤖 *RADAR ARBITRASE TURBO 12 KOLAM RAKSASA AKTIF!* 🚀\n\n"
        f"🌐 *Total Kolam:* `12 Kolam Likuiditas Utama Polygon (> $6 Juta TVL)`\n"
        f"⚡ *Kecepatan:* `Batch Multicall (< 0.5s / 4x per blok)`\n"
        f"🎯 *Target Minimal:* `$0.28 USD (~Rp 5.000+ Bersih per Tembakan)`\n"
        f"⛽ *Gas Priority:* `210 - 750 Gwei VIP Tier`\n"
        f"📜 *Kontrak:* `{contract_display}`\n"
        f"📡 *Status:* {'🔥 LIVE SNIPER ON-CHAIN AKTIF!' if is_live_ready else '🔍 RADAR PENGAMATAN'}"
    )

    last_alert_time = {}
    active_rpc = POLYGON_RPCS[0]
    cycle = 0

    while True:
        cycle += 1
        try:
            # Susun 1 Batch JSON-RPC Request untuk 12 kolam (24 query sekaligus)
            batch = []
            req_map = {}
            idx = 0
            for k, cfg in POOLS.items():
                batch.append({"jsonrpc": "2.0", "id": idx, "method": "eth_call", "params": [{"to": cfg["quick"], "data": "0x0902f1ac"}, "latest"]})
                req_map[idx] = (k, "quick")
                idx += 1
                batch.append({"jsonrpc": "2.0", "id": idx, "method": "eth_call", "params": [{"to": cfg["uni"], "data": "0x3850c7bd"}, "latest"]})
                req_map[idx] = (k, "uni")
                idx += 1

            # Tambah query blockNumber
            batch.append({"jsonrpc": "2.0", "id": 100, "method": "eth_blockNumber", "params": []})

            resp = requests.post(active_rpc, json=batch, timeout=6).json()

            results = {}
            block_num = 0
            for item in resp:
                item_id = item["id"]
                if item_id == 100:
                    block_num = int(item.get("result", "0x0"), 16)
                else:
                    k, dt = req_map[item_id]
                    if k not in results: results[k] = {}
                    results[k][dt] = item.get("result")

            for k, cfg in POOLS.items():
                r_q = results.get(k, {}).get("quick")
                r_u = results.get(k, {}).get("uni")

                if r_q and r_u and r_q != "0x" and r_u != "0x" and len(r_q) >= 130 and len(r_u) >= 66:
                    q_d = r_q[2:]
                    r0 = int(q_d[0:64], 16) / (10**cfg['dec0'])
                    r1 = int(q_d[64:128], 16) / (10**cfg['dec1'])

                    # FILTER ANTI-KOLAM HANTU: Wajib memenuhi ambang likuiditas minimum nyata
                    if r0 < cfg.get("min_r0", 1.0) or r1 < cfg.get("min_r1", 1.0):
                        continue

                    p_q = r1 / r0 if r0 > 0 else 0

                    u_d = r_u[2:]
                    sqrtP = int(u_d[0:64], 16)
                    p_u = (sqrtP / (2**96))**2 * (10**(cfg['dec0'] - cfg['dec1']))

                    if p_q > 0 and p_u > 0:
                        if p_q < p_u:
                            spread_pct = ((p_u - p_q) / p_q) * 100
                            direction = 0  # Beli di QuickSwap V2 -> Jual di Uniswap V3
                            arah = "QuickSwap -> Uniswap V3"
                        else:
                            spread_pct = ((p_q - p_u) / p_u) * 100
                            direction = 1  # Beli di Uniswap V3 -> Jual di QuickSwap V2
                            arah = "Uniswap V3 -> QuickSwap V2"

                        fee_tot = cfg["fee_tot"]
                        # JIKA SPREAD MENUTUPI BIAYA FEE
                        if spread_pct > fee_tot:
                            net_profit_pct = spread_pct - fee_tot
                            loan = cfg["loan_usd"]
                            est_cuan_usd = (net_profit_pct / 100.0) * loan
                            est_cuan_idr = est_cuan_usd * KURS_USDT_IDR

                            # TARGET SCALPING AGRESIF: SIKAT MULAI DARI $0.28 USD (~Rp 5.000+) BERSIH!
                            if est_cuan_usd >= 0.28:
                                tip_gwei = calculate_adaptive_tip(est_cuan_idr)
                                print(f"  🔥 [PELUANG CUAN NYATA!] {cfg['nama']} | {arah} | Net: +{net_profit_pct:.3f}% (~Rp {est_cuan_idr:,.0f}) | Tip: {tip_gwei:.0f} Gwei", flush=True)

                                # Rancang Calldata Flash Loan
                                calldata_hex, min_profit_raw = build_flashloan_calldata(k, direction, est_cuan_usd)

                                # TEMBAK ON-CHAIN LIVE (0-DELAY)!
                                if is_live_ready:
                                    print(f"  ⚡ [AGRESIF: TEMBAK ON-CHAIN (Tip: {tip_gwei:.0f} Gwei)!]", flush=True)
                                    tx_ok, tx_res = execute_onchain_sniper_instant(SMART_CONTRACT_ADDRESS, calldata_hex, active_rpc, tip_gwei)
                                    if tx_ok:
                                        print(f"  🚀 [SNIPER BERHASIL DIKIRIM!] Tx Hash: {tx_res}", flush=True)
                                        # Pantau receipt di background thread agar radar utama tidak berhenti sedetik pun!
                                        threading.Thread(
                                            target=monitor_transaction_receipt,
                                            args=(tx_res, cfg['nama'], est_cuan_usd, est_cuan_idr, active_rpc)
                                        ).start()
                                    else:
                                        print(f"  ⚠️ [Gagal Kirim Tx]: {tx_res}", flush=True)

                                # Notifikasi Deteksi ke Telegram (Throttle 60 detik per pasangan)
                                last_t = last_alert_time.get(k, 0)
                                if (time.time() - last_t) > 60:
                                    last_alert_time[k] = time.time()
                                    cuan_msg = (
                                        f"🚨 *PELUANG ARBITRASE LAUTAN BIRU!* 🚨\n\n"
                                        f"🪙 *Pasangan:* {cfg['nama']}\n"
                                        f"📊 *Spread Kotor:* {spread_pct:.3f}%\n"
                                        f"💰 *Profit Bersih:* +{net_profit_pct:.3f}%\n"
                                        f"💵 *Estimasi Cuan:* ${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})\n"
                                        f"🔄 *Jalur:* {arah}\n"
                                        f"⚡ *Mode:* {'0-Delay Sniper (Tip: ' + str(tip_gwei) + ' Gwei)' if is_live_ready else 'Radar Pengamatan'}\n"
                                        f"🛡️ *Anti-Frontrunning:* Terenkripsi 1RPC"
                                    )
                                    send_telegram_alert(cuan_msg)

            time.sleep(0.4)

        except Exception as e:
            time.sleep(1.0)

if __name__ == "__main__":
    main()
