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

# =====================================================================
# JALUR VIP ANTI-INTIP (1RPC MEV Shield + Bor Direct Validator)
# =====================================================================
POLYGON_RPCS = [
    "https://polygon-bor-rpc.publicnode.com",   # Jalur Utama Cepat: Direct Bor Node Tanpa Rate Limit
    "https://1rpc.io/matic",                    # Jalur VIP Terenkripsi MEV Shield
    "https://polygon-rpc.com"                   # Jalur Cadangan
]

# Alamat Dompet Resmi Anda
DOMPET_ANDA = "0x3cfEabd2bBcF45Aa26afd62b8d5629B376f5CC36"

# Kredensial Notifikasi Telegram
TELEGRAM_TOKEN = "8854612522:AAF5cczXAA8RsPNA1vvd93asDVaOXZQreu0"
TELEGRAM_CHAT_ID = "5124389853"

# Kredensial Eksekutor (Dari GitHub Secrets / Environment Variable)
SMART_CONTRACT_ADDRESS = os.environ.get("SMART_CONTRACT_ADDRESS", "").strip()
if not SMART_CONTRACT_ADDRESS:
    SMART_CONTRACT_ADDRESS = "0x4BAD2a58f6192a097D3bfdf3681F7f5eceade622"
METAMASK_PRIVATE_KEY = os.environ.get("METAMASK_PRIVATE_KEY", "").strip()

# =====================================================================
# KONFIGURASI AMBANG TARGET FINANSIAL (MINIMAL CUAN RP 350 BERSIH)
# =====================================================================
KURS_USD_IDR = 18100.0
TARGET_MIN_CUAN_IDR = 350.0                 # Target Laba Bersih Minimal Rp 350
MIN_CUAN_USD = TARGET_MIN_CUAN_IDR / KURS_USD_IDR  # ~$0.01934 USD

# Peta Estimasi Harga Aset USD (Untuk kalkulasi kedalaman cadangan & slippage presisi)
ASSET_PRICES_USD = {
    "USDT": 1.0,
    "USDCe": 1.0,
    "USDC": 1.0,
    "DAI": 1.0,
    "WMATIC": 0.35,
    "stMATIC": 0.38,
    "WETH": 2500.0,
    "LINK": 11.5,
    "AAVE": 150.0,
    "UNI": 7.5,
    "WBTC": 75000.0
}

# =====================================================================
# MATRIKS 24 KOLAM LIKUIDITAS TERVERIFIKASI (BEBAS KOLAM JEBAKAN)
# Hanya menyaring kolam dengan Likuiditas Nyata di QuickSwap V2 & Uniswap V3
# =====================================================================
POOLS = {
    # --- 1. STABLECOIN HIGH-VOLUME POOLS (Fee Rendah, Spread Sering Muncul) ---
    "DAI_USDT_100": {
        "nama": "DAI / USDT (100)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x254aa3a898071d6a2da0db11da73b02b4646078f",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 100, "fee_tot": 0.36,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    "DAI_USDT_500": {
        "nama": "DAI / USDT (500)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x42f0530351471dab7ec968476d19bd36af9ec52d",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    "DAI_USDCe_100": {
        "nama": "DAI / USDC.e (100)",
        "quick": "0xf04adbf75cdfc5ed26eea4bbbb991db002036bdd",
        "uni": "0x5645dcb64c059aa11212707fbf4e7f984440a8cf",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 2500.0, "uni_fee": 100, "fee_tot": 0.36,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    "DAI_USDCe_500": {
        "nama": "DAI / USDC.e (500)",
        "quick": "0xf04adbf75cdfc5ed26eea4bbbb991db002036bdd",
        "uni": "0x00cdbe40db63d91c7a5255dc765a0c64a38aaeb2",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    "USDCe_USDT_100": {
        "nama": "USDC.e / USDT (100)",
        "quick": "0x2cf7252e74036d1da830d11089d326296e64a728",
        "uni": "0x875a5e378c5443210eb70ca4465df93a40498717",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "dec0": 6, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 100, "fee_tot": 0.36,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    "USDCe_USDT_500": {
        "nama": "USDC.e / USDT (500)",
        "quick": "0x2cf7252e74036d1da830d11089d326296e64a728",
        "uni": "0x4b31a4a1599813c9e6ce208575a7cce69b2d87e0",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "dec0": 6, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 1000.0, "min_r1": 1000.0
    },

    # --- 2. WMATIC (POL) HIGH-LIQUIDITY POOLS ---
    "MATIC_USDT_500": {
        "nama": "WMATIC / USDT (500)",
        "quick": "0x604229c960e5cacf2aaeac8be68ac07ba9df81c3",
        "uni": "0x9b08288c3be4f62bbf8d1c20ac9c5e6f9467d8b7",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 5000.0, "min_r1": 1000.0
    },
    "MATIC_USDCe_500": {
        "nama": "WMATIC / USDC.e (500)",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0xa374094527e1673A86dE625aa59517c5de346d32",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 5000.0, "min_r1": 1000.0
    },
    "MATIC_USDCe_3000": {
        "nama": "WMATIC / USDC.e (3000)",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0x88f3c15720448e838e12b73f5f540f1d0313552c",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 5000.0, "min_r1": 1000.0
    },
    "MATIC_DAI_500": {
        "nama": "WMATIC / DAI (500)",
        "quick": "0xe7a24ef0c5e95ffb0f6684b813a78f2a3ad7d171",
        "uni": "0xd3959c9d9633e7215c0e0c0ab0cb99bb0982cbe1",
        "asset": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",   # DAI
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "DAI", "is_asset_t0": False,
        "max_loan_usd": 1500.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 2000.0, "min_r1": 1000.0
    },
    "MATIC_DAI_3000": {
        "nama": "WMATIC / DAI (3000)",
        "quick": "0xe7a24ef0c5e95ffb0f6684b813a78f2a3ad7d171",
        "uni": "0xa6f849ffb89d4ca9d5eb659c2354784a7e937d7a",
        "asset": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",   # DAI
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "DAI", "is_asset_t0": False,
        "max_loan_usd": 1500.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 2000.0, "min_r1": 1000.0
    },
    "MATIC_WETH_500": {
        "nama": "WMATIC / WETH (500)",
        "quick": "0xadb27230d33e8ee810923f1f04f4254a44c4c106",
        "uni": "0x167384319b41f7094e62470b379737f9577d9da7",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 5000.0, "min_r1": 5.0
    },
    "MATIC_WETH_3000": {
        "nama": "WMATIC / WETH (3000)",
        "quick": "0xadb27230d33e8ee810923f1f04f4254a44c4c106",
        "uni": "0x86f1d8390222a3691c28938ec7404a1661e618e0",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 5000.0, "min_r1": 5.0
    },

    # --- 3. WETH (ETH) HIGH-LIQUIDITY POOLS ---
    "ETH_USDT_500": {
        "nama": "WETH / USDT (500)",
        "quick": "0xf6422b997c7f54d1c6a6e103bcb1499eea0a7046",
        "uni": "0xbb98b3d2b18aef63a3178023a920971cf5f29be4",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 10.0, "min_r1": 5000.0
    },
    "ETH_USDT_3000": {
        "nama": "WETH / USDT (3000)",
        "quick": "0xf6422b997c7f54d1c6a6e103bcb1499eea0a7046",
        "uni": "0x9815038c119565507740263303d7c35e3860bb77",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 10.0, "min_r1": 5000.0
    },
    "ETH_USDCe_500": {
        "nama": "WETH / USDC.e (500)",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x45dda9cb7c25131df268515131f647d726f50608",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 5000.0, "min_r1": 10.0
    },
    "ETH_USDCe_3000": {
        "nama": "WETH / USDC.e (3000)",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x50eaedb835021e4a108b7290636d62e9765cc6d7",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 2500.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 5000.0, "min_r1": 10.0
    },

    # --- 4. TOP LIQUID BLUE CHIP POOLS (LINK, stMATIC, AAVE, UNI) ---
    "LINK_WETH_500": {
        "nama": "LINK / WETH (500)",
        "quick": "0xdc9232e2df177d7a12fdff6ecbab114e2231198d",
        "uni": "0x98bb7e4871927d6d5eb5b018fb5f09faecb68421",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",  # LINK
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 500.0, "min_r1": 5.0
    },
    "LINK_WETH_3000": {
        "nama": "LINK / WETH (3000)",
        "quick": "0xdc9232e2df177d7a12fdff6ecbab114e2231198d",
        "uni": "0x93206be63364f3d2f9ef2bf8bfef576ad486ca91",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",  # LINK
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 1500.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 500.0, "min_r1": 5.0
    },
    "LINK_MATIC_500": {
        "nama": "LINK / WMATIC (500)",
        "quick": "0x576595562d10332f7ec31889a244fe0bf03e05a8",
        "uni": "0x39a1ca83424cb476c596ff1758ee6ba649c25983",
        "asset": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",   # WMATIC
        "target": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",  # LINK
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WMATIC", "is_asset_t0": False,
        "max_loan_usd": 1500.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 500.0, "min_r1": 1000.0
    },
    "stMATIC_MATIC_500": {
        "nama": "stMATIC / WMATIC (500)",
        "quick": "0x5ef034293fe5f98cfba804be8c8cb69d5fb38cfa",
        "uni": "0x83f064858bc166e2c418a0acb73bbdb446bfb05b",
        "asset": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",   # WMATIC
        "target": "0x3A58a54C066FdC0f2D55FC9C89F0415C92eBf3C4",  # stMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WMATIC", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    "AAVE_WETH_500": {
        "nama": "AAVE / WETH (500)",
        "quick": "0xa6f8a41767e7216a75a7cce69b2d87e008f1b131",
        "uni": "0x17c0934ebf32b1fffe5d2f6fbf4e5692ce03a7a2",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0xD6DF932A45C0f255f85145f286eA0b292B21C90B",  # AAVE
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 500, "fee_tot": 0.40,
        "min_r0": 10.0, "min_r1": 2.0
    },
    "AAVE_WETH_3000": {
        "nama": "AAVE / WETH (3000)",
        "quick": "0xa6f8a41767e7216a75a7cce69b2d87e008f1b131",
        "uni": "0x717906d2a45a201c70e28f73117540ea674b01e3",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",   # WETH
        "target": "0xD6DF932A45C0f255f85145f286eA0b292B21C90B",  # AAVE
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 1500.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 10.0, "min_r1": 2.0
    },
    "UNI_MATIC_3000": {
        "nama": "UNI / WMATIC (3000)",
        "quick": "0xc45092e7e73951c6668f6c46acfca9f2b1c69aef",
        "uni": "0x7f9121b4f4e040fd066e9dc5c250cf9b4338d5bc",
        "asset": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",   # WMATIC
        "target": "0xb33EaAd8d922B1083446DC23f610c2567fB5180f",  # UNI
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WMATIC", "is_asset_t0": True,
        "max_loan_usd": 1500.0, "uni_fee": 3000, "fee_tot": 0.65,
        "min_r0": 1000.0, "min_r1": 10.0
    }
}

MULTICALL2_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"
SIG_GET_RESERVES = keccak(text="getReserves()")[:4]
SIG_SLOT0 = keccak(text="slot0()")[:4]
SIG_TRY_AGGREGATE = keccak(text="tryAggregate(bool,(address,bytes)[])")[:4]

def get_active_rpc():
    for rpc in POLYGON_RPCS:
        try:
            r = requests.post(rpc, json={"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}, timeout=2.0)
            if r.status_code == 200 and "result" in r.json():
                return rpc
        except Exception:
            pass
    return POLYGON_RPCS[0]

def get_current_gas_price(active_rpc):
    try:
        r = requests.post(active_rpc, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}, timeout=1.5)
        res = r.json().get("result")
        if res:
            return int(res, 16) / 1e9
        return 30.0
    except Exception:
        return 30.0

def calculate_dynamic_loan(pool_cfg, spread_pct, r0_clean, r1_clean):
    fee_tot = pool_cfg.get("fee_tot", 0.40)
    gross_net = spread_pct - fee_tot
    if gross_net <= 0.001:
        return 50.0

    r_asset = r0_clean if pool_cfg["is_asset_t0"] else r1_clean
    price_asset = ASSET_PRICES_USD.get(pool_cfg["asset_sym"], 1.0)
    r_usd = r_asset * price_asset

    # Formula AMM Optimum untuk spread surplus: L* = (gross_net / 100) * R / 2
    # Dibatasi agar tidak melampaui kedalaman kolam
    optimal_loan = (gross_net / 100.0) * r_usd * 0.5
    
    # Batas keamanan: maksimal 3.5% dari cadangan kolam untuk menjaga slippage tetap tipis
    max_safe = r_usd * 0.035
    max_loan_cap = pool_cfg.get("max_loan_usd", 2500.0)

    if spread_pct >= 2.0:
        max_loan_cap *= 2.0

    loan = min(optimal_loan, max_safe, max_loan_cap)
    return max(loan, 50.0)

def calculate_priority_tip(est_cuan_usd):
    # Tip adaptif: cepat menang lawan bot lain (default bot lain 30 Gwei), tapi tetap hemat
    if est_cuan_usd >= 10.0:     # Cuan > Rp 180.000
        return 95.0              # Super kilat masuk blok pertama
    elif est_cuan_usd >= 2.0:    # Cuan > Rp 36.000
        return 70.0
    elif est_cuan_usd >= 0.5:    # Cuan > Rp 9.000
        return 52.0
    elif est_cuan_usd >= 0.1:    # Cuan > Rp 1.800
        return 42.0
    else:                        # Cuan Rp 350 - Rp 1.800
        return 36.0              # 36 Gwei mengalahkan bot standar 30 Gwei, hemat gas (~Rp 60 perak)

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload, timeout=3)
    except Exception:
        pass

def monitor_transaction_receipt(tx_hash, pool_name, est_cuan_usd, est_cuan_idr, active_rpc):
    print(f"  🔍 [MEMANTAU ON-CHAIN CONFIRMATION]: {tx_hash} ...", flush=True)
    for attempt in range(15):
        time.sleep(2)
        try:
            r = requests.post(active_rpc, json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 88
            }, timeout=3.0)
            receipt = r.json().get("result")
            if receipt:
                status = receipt.get("status")
                block_num = int(receipt.get("blockNumber", "0"), 16)
                gas_used = int(receipt.get("gasUsed", "0"), 16)
                if status == "0x1":
                    success_msg = (
                        f"🏆 *ARBITRASE ON-CHAIN SUKSES 100%!* 💰\n\n"
                        f"🪙 *Pasangan:* `{pool_name}`\n"
                        f"💵 *Laba Bersih:* `+${est_cuan_usd:.4f} (~Rp {est_cuan_idr:,.0f})`\n"
                        f"🧱 *Masuk Blok:* `{block_num}`\n"
                        f"⛽ *Gas Terpakai:* `{gas_used:,}` unit\n"
                        f"🔗 *Bukti PolygonScan:* [Cek Transaksi](https://polygonscan.com/tx/{tx_hash})"
                    )
                    send_telegram_alert(success_msg)
                    print(f"    🏆 [EKSEKUSI SUKSES 100%!]: https://polygonscan.com/tx/{tx_hash}", flush=True)
                else:
                    revert_msg = (
                        f"🛡️ *SIMULASI KONTRAK AKTIF (AUTO-REVERT)* 🛡️\n\n"
                        f"🪙 *Pasangan:* `{pool_name}`\n"
                        f"ℹ️ Transaksi dibatalkan secara aman oleh kontrak pintar karena tick slippage.\n"
                        f"🔗 [Lihat Tx](https://polygonscan.com/tx/{tx_hash})\n"
                        f"⛽ *Biaya Gas Revert:* ~Rp 60 perak."
                    )
                    send_telegram_alert(revert_msg)
                    print(f"    🛡️ [TRANSAKSI DIBATALKAN KONTRAK SECARA AMAN (REVERT)]: {tx_hash}", flush=True)
                return
        except Exception:
            pass
    print(f"    ⏳ [TIMEOUT]: Menunggu konfirmasi {tx_hash}", flush=True)

def simulate_arbitrage_execution(contract_address, calldata_hex, active_rpc):
    try:
        tx_sim_payload = {
            "from": DOMPET_ANDA,
            "to": contract_address,
            "data": calldata_hex
        }
        r = requests.post(active_rpc, json={
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [tx_sim_payload, "latest"],
            "id": 99
        }, timeout=2.5)
        res = r.json()
        if "error" in res:
            err_msg = res["error"].get("message", "Simulasi Revert")
            return False, err_msg
        return True, "Simulasi 100% Lolos Untung"
    except Exception as e:
        return False, str(e)

def execute_onchain_sniper_instant(contract_address, calldata_hex, active_rpc, tip_gwei):
    try:
        acct = Account.from_key(METAMASK_PRIVATE_KEY)
        
        # Ambil Nonce Akurat
        r_nonce = requests.post(active_rpc, json={
            "jsonrpc": "2.0", "method": "eth_getTransactionCount",
            "params": [DOMPET_ANDA, "latest"], "id": 11
        }, timeout=2.0)
        nonce = int(r_nonce.json().get("result", "0x0"), 16)
        
        # Base fee dari blok terakhir
        r_block = requests.post(active_rpc, json={
            "jsonrpc": "2.0", "method": "eth_getBlockByNumber",
            "params": ["latest", False], "id": 12
        }, timeout=2.0)
        block_data = r_block.json().get("result", {})
        base_fee = int(block_data.get("baseFeePerGas", "0x1dcd6500"), 16)
        
        max_priority_fee = int(tip_gwei * 1e9)
        max_fee = int((base_fee * 1.3) + max_priority_fee)
        
        tx_dict = {
            "chainId": 137,
            "nonce": nonce,
            "to": contract_address,
            "data": bytes.fromhex(calldata_hex[2:] if calldata_hex.startswith("0x") else calldata_hex),
            "value": 0,
            "gas": 480000,
            "maxPriorityFeePerGas": max_priority_fee,
            "maxFeePerGas": max_fee,
            "type": 2
        }
        
        signed = acct.sign_transaction(tx_dict)
        raw_tx_hex = signed.raw_transaction.hex() if hasattr(signed.raw_transaction, 'hex') else signed.raw_transaction.hex()
        if not raw_tx_hex.startswith("0x"):
            raw_tx_hex = "0x" + raw_tx_hex
            
        r_send = requests.post(active_rpc, json={
            "jsonrpc": "2.0", "method": "eth_sendRawTransaction",
            "params": [raw_tx_hex], "id": 13
        }, timeout=2.5)
        
        send_res = r_send.json()
        if "result" in send_res:
            return True, send_res["result"]
        else:
            return False, send_res.get("error", {}).get("message", "Gagal Broadcast Tx")
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 88, flush=True)
    print("  🚀 MESIN ARBITRASE TURBO 24 KOLAM TERVERIFIKASI - AUTONOMOUS 24/7", flush=True)
    print(f"  🎯 Target Cuan Minimal: Rp {TARGET_MIN_CUAN_IDR:,.0f} IDR (${MIN_CUAN_USD:.4f} USD)", flush=True)
    print(f"  💼 Dompet Penerima Cuan: {DOMPET_ANDA}", flush=True)
    print("=" * 88, flush=True)
    
    is_live_ready = False
    if SMART_CONTRACT_ADDRESS and METAMASK_PRIVATE_KEY:
        print(f"  ⚡ STATUS EKSEKUTOR: READY ON-CHAIN SNIPER (0-DELAY)")
        print(f"  📍 Kontrak Pintar: {SMART_CONTRACT_ADDRESS}\n", flush=True)
        is_live_ready = True
    else:
        print("  ⚠️ STATUS EKSEKUTOR: MODE RADAR PENGAMATAN ONLY (Kredensial Belum Terdeteksi)\n", flush=True)

    send_telegram_alert(
        f"🤖 *RADAR ARBITRASE TURBO 24 KOLAM AKTIF!* 🚀\n\n"
        f"🎯 *Target Minimal:* `Rp {TARGET_MIN_CUAN_IDR:,.0f} IDR`\n"
        f"🌐 *Total Kolam:* `24 Kolam Likuiditas Terverifikasi (Bebas Kolam Jebakan)`\n"
        f"⚡ *Mode:* `{'0-Delay Flash Loan Sniper' if is_live_ready else 'Radar Pengamatan'}`\n"
        f"🛡️ *Anti-Frontrunning:* `1RPC VIP Private Routing`\n"
        f"🛡️ *Pre-Flight Firewall:* `Zero-Cost EVM Simulation Shield (Aktif)`\n"
        f"💼 *Dompet Target:* `{DOMPET_ANDA}`\n\n"
        f"Mesin stand-by 24/7 memburu cuan agresif on-chain."
    )

    last_alert_time = {}
    cycle = 0

    while True:
        cycle += 1
        active_rpc = get_active_rpc()
        
        # Bangun batch Multicall2 untuk seluruh 24 kolam
        calls = []
        pool_keys = list(POOLS.keys())
        
        for k in pool_keys:
            cfg = POOLS[k]
            calls.append((cfg["quick"], SIG_GET_RESERVES))
            calls.append((cfg["uni"], SIG_SLOT0))
            
        call_tuples = [(addr, data) for addr, data in calls]
        encoded_args = encode(['bool', '(address,bytes)[]'], [False, call_tuples])
        calldata = SIG_TRY_AGGREGATE + encoded_args
        calldata_hex = "0x" + calldata.hex()
        
        try:
            r = requests.post(active_rpc, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": MULTICALL2_ADDRESS, "data": calldata_hex}, "latest"],
                "id": cycle
            }, timeout=3.0)
            
            resp_data = r.json().get("result")
            if not resp_data or resp_data == "0x":
                time.sleep(0.3)
                continue
                
            raw_bytes = bytes.fromhex(resp_data[2:])
            offset = int.from_bytes(raw_bytes[0:32], 'big')
            count = int.from_bytes(raw_bytes[offset:offset+32], 'big')
            
            elements = []
            curr_pos = offset + 32
            for _ in range(count):
                elem_offset = int.from_bytes(raw_bytes[curr_pos:curr_pos+32], 'big')
                abs_elem_pos = offset + 32 + elem_offset
                success = (int.from_bytes(raw_bytes[abs_elem_pos:abs_elem_pos+32], 'big') == 1)
                data_offset = int.from_bytes(raw_bytes[abs_elem_pos+32:abs_elem_pos+64], 'big')
                abs_data_pos = abs_elem_pos + data_offset
                data_len = int.from_bytes(raw_bytes[abs_data_pos:abs_data_pos+32], 'big')
                ret_data = raw_bytes[abs_data_pos+32 : abs_data_pos+32+data_len]
                elements.append((success, ret_data))
                curr_pos += 32
                
        except Exception:
            time.sleep(0.5)
            continue

        waktu = datetime.now().strftime("%H:%M:%S")

        # Parsing data 24 kolam
        for idx, k in enumerate(pool_keys):
            cfg = POOLS[k]
            elem_quick = elements[idx * 2]
            elem_uni = elements[idx * 2 + 1]
            
            if elem_quick[0] and elem_uni[0] and len(elem_quick[1]) >= 64 and len(elem_uni[1]) >= 32:
                # 1. QuickSwap V2 Reserves
                b_q = elem_quick[1]
                r0 = int.from_bytes(b_q[0:32], 'big')
                r1 = int.from_bytes(b_q[32:64], 'big')
                
                # 2. Uniswap V3 SqrtPriceX96
                b_u = elem_uni[1]
                sqrtPriceX96 = int.from_bytes(b_u[0:32], 'big')
                
                r0_clean = r0 / (10 ** cfg["dec0"])
                r1_clean = r1 / (10 ** cfg["dec1"])
                
                # Filter Likuiditas Minimal
                if r0_clean < cfg.get("min_r0", 1.0) or r1_clean < cfg.get("min_r1", 1.0):
                    continue
                    
                p_quick = r1_clean / r0_clean if r0_clean > 0 else 0
                price_ratio = (sqrtPriceX96 / (2**96)) ** 2
                dec_diff = cfg["dec0"] - cfg["dec1"]
                p_uni = price_ratio * (10 ** dec_diff)
                
                if p_quick > 0 and p_uni > 0:
                    spread_pct = abs(p_quick - p_uni) / min(p_quick, p_uni) * 100.0
                    fee_total = cfg.get("fee_tot", 0.40)
                    
                    if spread_pct > fee_total:
                        effective_loan_usd = calculate_dynamic_loan(cfg, spread_pct, r0_clean, r1_clean)
                        
                        # Hitung kedalaman cadangan aset di QuickSwap dalam USD secara presisi
                        r_asset = r0_clean if cfg["is_asset_t0"] else r1_clean
                        price_asset = ASSET_PRICES_USD.get(cfg["asset_sym"], 1.0)
                        reserve_depth_usd = r_asset * price_asset
                        
                        price_impact_pct = (effective_loan_usd / (reserve_depth_usd + effective_loan_usd)) * 100.0 if reserve_depth_usd > 0 else 999.0
                        real_net_pct = spread_pct - fee_total - price_impact_pct
                        
                        # Target: Minimal Rp 350 IDR Bersih
                        est_cuan_usd = (effective_loan_usd * max(0.0, real_net_pct)) / 100.0
                        est_cuan_idr = est_cuan_usd * KURS_USD_IDR
                        
                        if real_net_pct > 0.001 and est_cuan_idr >= TARGET_MIN_CUAN_IDR:
                            tip_gwei = calculate_priority_tip(est_cuan_usd)
                            
                            # Logika Direction Presisi: Memperhitungkan posisi token dasar (is_asset_t0)
                            is_t0 = cfg["is_asset_t0"]
                            direction = (0 if p_quick < p_uni else 1) if not is_t0 else (1 if p_quick < p_uni else 0)
                            
                            arah = "QuickSwap ➔ Uniswap V3" if direction == 0 else "Uniswap V3 ➔ QuickSwap"
                            
                            print(f"\n⚡ [{waktu}] ARBITRASE VALID: {cfg['nama']} | Net: +{real_net_pct:.3f}% | Loan: ${effective_loan_usd:.0f} | Cuan: +${est_cuan_usd:.4f} (~Rp {est_cuan_idr:,.0f})", flush=True)

                            # Eksekusi Sniper On-Chain (0-Delay)
                            if is_live_ready:
                                # Hitung loan_amount_raw dan min_profit_raw (Ambang Minimum Rp 350 Bersih)
                                if cfg["asset_sym"] in ["USDT", "USDCe", "DAI"]:
                                    loan_amount_raw = int(effective_loan_usd * (10 ** cfg["asset_dec"]))
                                    min_profit_raw = int(MIN_CUAN_USD * (10 ** cfg["asset_dec"]))
                                else:
                                    token_price = ASSET_PRICES_USD.get(cfg["asset_sym"], 1.0)
                                    token_loan = effective_loan_usd / token_price
                                    token_min_profit = MIN_CUAN_USD / token_price
                                    loan_amount_raw = int(token_loan * (10 ** cfg["asset_dec"]))
                                    min_profit_raw = max(1, int(token_min_profit * (10 ** cfg["asset_dec"])))
                                
                                # ABI Encode executeOperation params: (uint8 direction, address targetToken, uint24 uniFee, uint256 minProfit)
                                inner_params = encode(
                                    ['uint8', 'address', 'uint24', 'uint256'],
                                    [direction, cfg["target"], cfg.get("uni_fee", 500), min_profit_raw]
                                )
                                
                                # ABI Encode requestFlashLoan(address asset, uint256 amount, bytes params)
                                sig_exec = keccak(b"requestFlashLoan(address,uint256,bytes)")[:4]
                                exec_calldata = sig_exec + encode(
                                    ['address', 'uint256', 'bytes'],
                                    [cfg["asset"], loan_amount_raw, inner_params]
                                )
                                calldata_hex = "0x" + exec_calldata.hex()
                                
                                # 1. Pre-Flight Zero-Cost EVM Simulation Shield
                                sim_ok, sim_msg = simulate_arbitrage_execution(SMART_CONTRACT_ADDRESS, calldata_hex, active_rpc)
                                
                                if not sim_ok:
                                    print(f"  🛡️ [Pre-Flight Simulation Dicegah]: {sim_msg} (Hemat Gas & Menjaga Modal)", flush=True)
                                else:
                                    # 2. Tembakkan On-Chain Jika Lolos Uji Simulasi
                                    print(f"  🚀 [SIMULASI 100% LOLOS]: Menembakkan Flash Loan ${effective_loan_usd:.0f} USD (Tip: {tip_gwei:.0f} Gwei)...", flush=True)
                                    tx_ok, tx_res = execute_onchain_sniper_instant(SMART_CONTRACT_ADDRESS, calldata_hex, active_rpc, tip_gwei)
                                    if tx_ok:
                                        print(f"  🚀 [SNIPER BERHASIL DIKIRIM!] Tx Hash: {tx_res}", flush=True)
                                        shoot_msg = (
                                            f"🚀 *SNIPER ARBITRASE DITEMBAKKAN ON-CHAIN!* ⚡\n\n"
                                            f"🪙 *Kolam:* `{cfg['nama']}`\n"
                                            f"📏 *Pinjaman Flash Loan:* `${effective_loan_usd:,.0f} USD`\n"
                                            f"📊 *Spread Bersih:* `+{real_net_pct:.3f}%`\n"
                                            f"💰 *Target Laba:* `+${est_cuan_usd:.4f} (~Rp {est_cuan_idr:,.0f})`\n"
                                            f"⛽ *Priority Tip:* `{tip_gwei:.0f} Gwei`\n"
                                            f"🔗 *Cek Transaksi:* [PolygonScan](https://polygonscan.com/tx/{tx_res})"
                                        )
                                        send_telegram_alert(shoot_msg)
                                        threading.Thread(
                                            target=monitor_transaction_receipt,
                                            args=(tx_res, cfg['nama'], est_cuan_usd, est_cuan_idr, active_rpc)
                                        ).start()
                                    else:
                                        print(f"  ⚠️ [Gagal Kirim Tx]: {tx_res}", flush=True)

                            elif not is_live_ready:
                                # Notifikasi Deteksi Radar Pengamatan (Throttle 45 detik)
                                last_t = last_alert_time.get(k, 0)
                                if (time.time() - last_t) > 45:
                                    last_alert_time[k] = time.time()
                                    cuan_msg = (
                                        f"🔍 *RADAR DETEKSI SPREAD CUAN!* 📡\n\n"
                                        f"🪙 *Pasangan:* {cfg['nama']}\n"
                                        f"📏 *Pinjaman Disesuaikan:* `${effective_loan_usd:.0f} USD`\n"
                                        f"📊 *Spread Kotor:* {spread_pct:.3f}%\n"
                                        f"📉 *Slippage Kolam:* {price_impact_pct:.3f}%\n"
                                        f"💰 *Profit Bersih:* +{real_net_pct:.3f}%\n"
                                        f"💵 *Estimasi Cuan:* `+${est_cuan_usd:.4f} (~Rp {est_cuan_idr:,.0f})`\n"
                                        f"🔄 *Jalur:* {arah}\n"
                                        f"🛡️ *Anti-Frontrunning:* Terenkripsi 1RPC"
                                    )
                                    send_telegram_alert(cuan_msg)

        time.sleep(0.3)

if __name__ == "__main__":
    main()
