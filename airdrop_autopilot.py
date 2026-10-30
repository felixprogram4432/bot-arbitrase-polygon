import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import random
import requests
from eth_account import Account
from eth_utils import keccak, to_checksum_address
from eth_abi import encode

# ============================================================
# KONFIGURASI DOMPET AIRDROP HUNTER BAYU
# ============================================================
PRIVATE_KEY = "5ae4f9140c5b467a99da41d1418109704c4f0301fef160ce8719832deb45452b"
ACCOUNT = Account.from_key(PRIVATE_KEY)
WALLET_ADDR = ACCOUNT.address

# TELEGRAM CONFIG
TELEGRAM_TOKEN = "8854612522:AAF5cczXAA8RsPNA1vvd93asDVaOXZQreu0"
TELEGRAM_CHAT_ID = "5124389853"

def send_telegram_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=8)
    except Exception:
        pass

# 10 JARINGAN TIER-1 PALING BERGENGSI DI DUNIA KRIPTO SAAT INI
NETWORKS = {
    "sepolia": {
        "name": "Ethereum Sepolia (L1 Base)",
        "chainId": 11155111,
        "rpc": "https://ethereum-sepolia-rpc.publicnode.com",
        "explorer": "https://sepolia.etherscan.io",
        "symbol": "SepoliaETH"
    },
    "linea_sepolia": {
        "name": "Linea Sepolia (Consensys Rp 110T)",
        "chainId": 59141,
        "rpc": "https://rpc.sepolia.linea.build",
        "explorer": "https://sepolia.lineascan.build",
        "symbol": "LineaETH"
    },
    "base_sepolia": {
        "name": "Base Sepolia (Coinbase L2)",
        "chainId": 84532,
        "rpc": "https://sepolia.base.org",
        "explorer": "https://sepolia.basescan.org",
        "symbol": "BaseETH"
    },
    "arbitrum_sepolia": {
        "name": "Arbitrum Sepolia (Raja L2)",
        "chainId": 421614,
        "rpc": "https://sepolia-rollup.arbitrum.io/rpc",
        "explorer": "https://sepolia.arbiscan.io",
        "symbol": "ArbETH"
    },
    "optimism_sepolia": {
        "name": "OP Sepolia (Superchain)",
        "chainId": 11155420,
        "rpc": "https://sepolia.optimism.io",
        "explorer": "https://sepolia-optimism.etherscan.io",
        "symbol": "OpETH"
    },
    "unichain_sepolia": {
        "name": "Unichain Sepolia (Uniswap L2)",
        "chainId": 1301,
        "rpc": "https://sepolia.unichain.org",
        "explorer": "https://sepolia.uniscan.xyz",
        "symbol": "UniETH"
    },
    "ink_sepolia": {
        "name": "Ink Sepolia (Kraken L2 Baru)",
        "chainId": 763373,
        "rpc": "https://rpc-gel-sepolia.inkonchain.com",
        "explorer": "https://explorer-sepolia.inkonchain.com",
        "symbol": "InkETH"
    },
    "monad_testnet": {
        "name": "Monad Testnet (Hype $225M L1)",
        "chainId": 10143,
        "rpc": "https://testnet-rpc.monad.xyz",
        "explorer": "https://testnet.monadexplorer.com",
        "symbol": "MON"
    },
    "zksync_sepolia": {
        "name": "ZkSync Sepolia (zkRollup Pioneer)",
        "chainId": 300,
        "rpc": "https://sepolia.era.zksync.dev",
        "explorer": "https://sepolia.explorer.zksync.io",
        "symbol": "ETH"
    },
    "polygon_amoy": {
        "name": "Polygon Amoy (Next-Gen)",
        "chainId": 80002,
        "rpc": "https://polygon-amoy-bor-rpc.publicnode.com",
        "explorer": "https://amoy.polygonscan.com",
        "symbol": "POL"
    }
}

# BYTECODE SMART CONTRACT STORAGE RESMI (100% EVM STANDAR)
RUNTIME_CODE = (
    "6080604052348015600e575f5ffd5b50600436106030575f3560e01c80632e64cec1146034578063"
    "6057361d14604e575b5f5ffd5b603a6066565b60405160459190608d565b60405180910390f35b60"
    "6460048036038101906060919060cd565b606e565b005b5f5f54905090565b805f8190555050565b"
    "5f819050919050565b6087816077565b82525050565b5f602082019050609e5f8301846080565b92"
    "915050565b5f5ffd5b60af816077565b811460b8575f5ffd5b50565b5f8135905060c78160a8565b"
    "92915050565b5f6020828403121560df5760de60a4565b5b5f60ea8482850160bb565b9150509291"
    "505056fea2646970667358221220234b4aa7ccc4df3761148a80826d3992be36c2c1cc06baaba3a9"
    "d0949c04f83664736f6c63430008220033"
)
CREATION_BYTECODE = "0x610129600e6000396101296000f3" + RUNTIME_CODE

def get_balance(rpc_url):
    try:
        r = requests.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [WALLET_ADDR, "latest"]
        }, timeout=6).json()
        wei = int(r.get("result", "0x0"), 16)
        return wei / 1e18
    except Exception:
        return 0.0

def get_nonce(rpc_url):
    try:
        r = requests.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 2, "method": "eth_getTransactionCount", "params": [WALLET_ADDR, "latest"]
        }, timeout=6).json()
        return int(r.get("result", "0x0"), 16)
    except Exception:
        return 0

def get_base_fee_and_tip(rpc_url):
    try:
        r = requests.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 3, "method": "eth_getBlockByNumber", "params": ["latest", False]
        }, timeout=6).json()
        b = r.get("result", {})
        base_fee = int(b.get("baseFeePerGas", "0x3b9aca00"), 16)
        tip = int(1.2 * 1e9)
        max_fee = int(base_fee * 1.3) + tip
        return tip, max_fee
    except Exception:
        return int(1.2 * 1e9), int(3.0 * 1e9)

def deploy_new_smart_contract(net_key):
    cfg = NETWORKS[net_key]
    rpc = cfg["rpc"]
    print(f"\n🚀 [DEPLOYER]: Memulai Deploy Smart Contract di {cfg['name']}...")
    
    bal = get_balance(rpc)
    print(f"💰 Saldo Dompet: {bal:.4f} {cfg['symbol']}")
    if bal < 0.0003:
        print("⚠️ Saldo tidak cukup untuk bayar gas di jaringan ini!")
        return None
        
    nonce = get_nonce(rpc)
    tip, max_fee = get_base_fee_and_tip(rpc)
    
    tx_dict = {
        "chainId": cfg["chainId"],
        "nonce": nonce,
        "data": bytes.fromhex(CREATION_BYTECODE[2:]),
        "value": 0,
        "gas": 350000,
        "maxPriorityFeePerGas": tip,
        "maxFeePerGas": max_fee,
        "type": 2
    }
    
    signed = Account.sign_transaction(tx_dict, PRIVATE_KEY)
    tx_hex = "0x" + signed.raw_transaction.hex()
    
    r_send = requests.post(rpc, json={
        "jsonrpc": "2.0", "id": 4, "method": "eth_sendRawTransaction", "params": [tx_hex]
    }, timeout=10).json()
    
    if "error" in r_send:
        print(f"❌ Gagal Deploy: {r_send['error']}")
        return None
        
    tx_hash = r_send.get("result")
    print(f"✅ Transaksi Deploy Berhasil Dikirim On-Chain!")
    print(f"🔗 Tx Hash: {tx_hash}")
    print(f"🌐 Cek Explorer: {cfg['explorer']}/tx/{tx_hash}")
    
    print("⏳ Menunggu konfirmasi blok...")
    for _ in range(12):
        time.sleep(2)
        try:
            r_rec = requests.post(rpc, json={
                "jsonrpc": "2.0", "id": 5, "method": "eth_getTransactionReceipt", "params": [tx_hash]
            }, timeout=6).json()
            rec = r_rec.get("result")
            if rec and rec.get("contractAddress"):
                c_addr = rec["contractAddress"]
                print(f"🎉 SUKSES! Smart Contract Baru Terbit: {c_addr}")
                print(f"👑 Status Dompet: RESMI MENJADI SMART CONTRACT CREATOR DI {cfg['name'].upper()}!")
                return c_addr
        except Exception:
            pass
            
    return None

def interact_with_contract(contract_addr, number_to_store=None, net_key="sepolia"):
    cfg = NETWORKS[net_key]
    rpc = cfg["rpc"]
    if number_to_store is None:
        number_to_store = random.randint(100, 999999)
        
    print(f"\n⚡ [INTERAKSI]: Menyimpan angka {number_to_store} ke dalam Smart Contract...")
    
    nonce = get_nonce(rpc)
    tip, max_fee = get_base_fee_and_tip(rpc)
    
    sig = keccak(b"store(uint256)")[:4].hex()
    calldata = "0x" + sig + encode(['uint256'], [number_to_store]).hex()
    
    tx_dict = {
        "chainId": cfg["chainId"],
        "nonce": nonce,
        "to": to_checksum_address(contract_addr),
        "data": bytes.fromhex(calldata[2:]),
        "value": 0,
        "gas": 120000,
        "maxPriorityFeePerGas": tip,
        "maxFeePerGas": max_fee,
        "type": 2
    }
    
    signed = Account.sign_transaction(tx_dict, PRIVATE_KEY)
    tx_hex = "0x" + signed.raw_transaction.hex()
    
    r_send = requests.post(rpc, json={
        "jsonrpc": "2.0", "id": 6, "method": "eth_sendRawTransaction", "params": [tx_hex]
    }, timeout=10).json()
    
    if "error" in r_send:
        print(f"❌ Gagal Interaksi: {r_send['error']}")
        return False
        
    tx_hash = r_send.get("result")
    print(f"✅ Interaksi Kontrak Sukses!")
    print(f"🔗 Tx Hash: {tx_hash}")
    print(f"🌐 Cek Bukti: {cfg['explorer']}/tx/{tx_hash}")
    return True

def bridge_funds_to_l2(dest_net_key, amount_eth=0.003):
    sep_rpc = NETWORKS["sepolia"]["rpc"]
    print(f"\n🌉 [AUTONOMOUS BRIDGE]: Mengirim {amount_eth} SepoliaETH ke {NETWORKS[dest_net_key]['name']}...")
    
    amount_wei = int(amount_eth * 1e18)
    nonce = get_nonce(sep_rpc)
    tip, max_fee = get_base_fee_and_tip(sep_rpc)
    
    if dest_net_key == "base_sepolia":
        # Base Sepolia L1StandardBridge
        target = to_checksum_address("0xfd0Bf71F60660E2f608ed56e1659C450eB113120")
        sig = bytes.fromhex("e11013dd")
        calldata = sig + encode(['address', 'uint32', 'bytes'], [to_checksum_address(WALLET_ADDR), 200000, b"superbridge"])
        gas = 250000
    elif dest_net_key == "optimism_sepolia":
        # OptimismPortalProxy
        target = to_checksum_address("0x16Fc5058F25648f994557aEd7Fd9BADC6a5f782c")
        sig = keccak(b"depositTransaction(address,uint256,uint64,bool,bytes)")[:4]
        calldata = sig + encode(['address', 'uint256', 'uint64', 'bool', 'bytes'], [to_checksum_address(WALLET_ADDR), amount_wei, 100000, False, b""])
        gas = 250000
    elif dest_net_key == "unichain_sepolia":
        # Unichain L1StandardBridge
        target = to_checksum_address("0x81014F44b0a345033bB2b3B21C7a1A308B35fEeA")
        sig = bytes.fromhex("e11013dd")
        calldata = sig + encode(['address', 'uint32', 'bytes'], [to_checksum_address(WALLET_ADDR), 200000, b""])
        gas = 250000
    elif dest_net_key == "ink_sepolia":
        # Ink OptimismPortal
        target = to_checksum_address("0x5d66c1782664115999c47c9fa5cd031f495d3e4f")
        sig = keccak(b"depositTransaction(address,uint256,uint64,bool,bytes)")[:4]
        calldata = sig + encode(['address', 'uint256', 'uint64', 'bool', 'bytes'], [to_checksum_address(WALLET_ADDR), amount_wei, 100000, False, b""])
        gas = 250000
    elif dest_net_key == "arbitrum_sepolia":
        # Arbitrum Delayed Inbox
        target = to_checksum_address("0xaAe29B0366299461418F5324a79Afc425BE5ae21")
        sig = keccak(b"depositEth(uint256)")[:4]
        calldata = sig + encode(['uint256'], [0])
        gas = 300000
    else:
        print(f"❌ Jaringan {dest_net_key} belum didukung untuk direct L1 bridge.")
        return None

    tx_dict = {
        "chainId": 11155111,
        "nonce": nonce,
        "to": target,
        "value": amount_wei,
        "data": calldata,
        "gas": gas,
        "maxPriorityFeePerGas": tip,
        "maxFeePerGas": max_fee,
        "type": 2
    }
    
    signed = Account.sign_transaction(tx_dict, PRIVATE_KEY)
    r_send = requests.post(sep_rpc, json={
        "jsonrpc": "2.0", "id": 10, "method": "eth_sendRawTransaction", "params": ["0x" + signed.raw_transaction.hex()]
    }, timeout=10).json()
    
    if "error" in r_send:
        print(f"❌ Gagal Bridge: {r_send['error']}")
        return None
        
    tx_hash = r_send.get("result")
    print(f"✅ Transaksi Bridge Berhasil Terkirim On-Chain!")
    print(f"🔗 Tx Hash: {tx_hash}")
    print(f"🌐 Cek Bukti L1: https://sepolia.etherscan.io/tx/{tx_hash}")
    return tx_hash

def watch_and_blast_loop(rounds=10, delay_sec=20):
    print("\n" + "=" * 80)
    print("🛰️ MODE RADAR AKTIF: MEMANTAU KEDATANGAN SALDO BRIDGE & AUTO-DEPLOY...")
    print("=" * 80)
    show_status()
    for r in range(rounds):
        print(f"\n⏱️ [Pemeriksaan Putaran #{r+1}/{rounds}]...")
        executed_any = False
        for k, v in NETWORKS.items():
            if k == "sepolia":
                continue
            bal = get_balance(v["rpc"])
            nonce = get_nonce(v["rpc"])
            if bal >= 0.0005 and nonce == 0:
                print(f"\n🎉 SALDO TERDETEKSI DI {v['name'].upper()}! (Saldo: {bal:.4f} {v['symbol']})")
                print(f"🚀 Menjalankan Auto-Deploy & Interaksi Kontrak Sekarang...")
                c_addr = deploy_new_smart_contract(k)
                if c_addr:
                    time.sleep(3)
                    interact_with_contract(c_addr, random.randint(100, 9999), k)
                    executed_any = True
                time.sleep(2)
        if not executed_any:
            print("⏳ Belum ada saldo baru yang mendarat dari validator L2. Menunggu putaran berikutnya...")
        time.sleep(delay_sec)
    print("\n🏁 Selesai Siklus Pemantauan.")
    show_status()

def show_status():
    print("\n" + "=" * 80)
    print("📋 MATRIKS 8 JARINGAN AIRDROP HUNTER MAS BAYU (LIVE ON-CHAIN)")
    print("=" * 80)
    print(f"💼 Alamat Dompet : {WALLET_ADDR}")
    print("-" * 80)
    for k, v in NETWORKS.items():
        bal = get_balance(v["rpc"])
        nonce = get_nonce(v["rpc"])
        status_gas = "🟢 Siap Tempur" if bal >= 0.0005 else "⚪ Butuh Gas"
        print(f"🌐 {v['name']:35} | Saldo: {bal:.4f} {v['symbol']:10} | Nonce: #{nonce:02d} | {status_gas}")
    print("=" * 80)

def auto_farm_all_ready_networks():
    show_status()
    print("\n🚀 [MULTI-CHAIN BLAST]: Memulai Auto-Farming ke SEMUA jaringan yang ada saldonya...")
    success_count = 0
    results = []
    for k, v in NETWORKS.items():
        bal = get_balance(v["rpc"])
        if bal >= 0.0005:
            print(f"\n=======================================================")
            print(f"🎯 Target Aktif: {v['name']}")
            print(f"=======================================================")
            c_addr = deploy_new_smart_contract(k)
            if c_addr:
                time.sleep(3)
                interact_with_contract(c_addr, random.randint(100, 9999), k)
                success_count += 1
                results.append({
                    "name": v["name"],
                    "contract": c_addr,
                    "tx_url": f"{v['explorer']}/address/{c_addr}"
                })
            time.sleep(2)
        else:
            print(f"⏩ Melewati {v['name']} (Belum ada saldo gas).")
            
    print(f"\n✨ Selesai! Berhasil mengeksekusi di {success_count} jaringan sekaligus!")
    show_status()
    
    if success_count > 0:
        summary_msg = (
            f"🤖 <b>LAPORAN HARIAN AIRDROP HUNTER MAS BAYU</b>\n"
            f"💼 Dompet: <code>{WALLET_ADDR}</code>\n"
            f"🎯 Eksekusi Sukses di <b>{success_count} Jaringan</b>!\n\n"
        )
        for res in results:
            summary_msg += f"• <b>{res['name']}</b>\n  📜 Kontrak: <code>{res['contract']}</code>\n  🔗 <a href='{res['tx_url']}'>Cek Explorer</a>\n\n"
        summary_msg += "👑 <i>Status Dompet: 100% Aktif Sebagai Smart Contract Creator!</i>"
        send_telegram_alert(summary_msg)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        auto_farm_all_ready_networks()
    else:
        print("\n🤖 AIRDROP HUNTER MULTI-CHAIN AUTO-PILOT (AI ENGINE)")
        print("Pilih aksi:")
        print("1. Multi-Chain Blast (Auto-Farm SEMUA Jaringan yang Ada Saldonya Sekaligus)")
        print("2. Cek Saldo & Status 8 Jaringan On-Chain")
        print("3. Deploy & Interaksi Khusus Sepolia")
        print("4. Deploy & Interaksi Khusus Linea Sepolia")
        print("5. Autonomous Bridge ke Seluruh L2 (OP, Arbitrum, Unichain, Ink)")
        print("6. Radar Watcher (Pantau Kedatangan Saldo & Langsung Auto-Deploy)")
        try:
            choice = input("\nMasukkan pilihan (1/2/3/4/5/6) [Default 1]: ").strip()
        except Exception:
            choice = "1"
            
        if choice == "2":
            show_status()
        elif choice == "3":
            deploy_new_smart_contract("sepolia")
        elif choice == "4":
            deploy_new_smart_contract("linea_sepolia")
        elif choice == "5":
            for n in ["optimism_sepolia", "arbitrum_sepolia", "unichain_sepolia", "ink_sepolia"]:
                bridge_funds_to_l2(n, 0.003)
                time.sleep(3)
        elif choice == "6":
            watch_and_blast_loop()
        else:
            auto_farm_all_ready_networks()
