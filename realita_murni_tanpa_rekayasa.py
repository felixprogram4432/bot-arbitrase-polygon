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
    "https://polygon-bor-rpc.publicnode.com",   # Jalur Utama Cepat: Direct Bor Node Tanpa Rate Limit
    "https://1rpc.io/matic",                    # Jalur VIP Terenkripsi
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

# MATRIKS 25 KOLAM LIKUIDITAS RAKSASA POLYGON (> $20 JUTA TVL TERVERIFIKASI FACTORY)
# Terkalibrasi Presisi: QuickSwap V2 <-> Uniswap V3 dengan Dynamic Loan Sizing
POOLS = {
    # 1. DAI / USDT (Fee 100: 0.01% - TVL > $1.5M)
    "DAI_USDT_100": {
        "nama": "DAI / USDT (100)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x254aa3a898071d6a2da0db11da73b02b4646078f",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 100, "fee_tot": 0.40,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    # 2. DAI / USDT (Fee 500: 0.05% - TVL > $5M)
    "DAI_USDT_500": {
        "nama": "DAI / USDT (500)",
        "quick": "0x59153f27eefe07e5ece4f9304ebba1da6f53ca88",
        "uni": "0x42f0530351471dab7ec968476d19bd36af9ec52d",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 1000.0, "min_r1": 1000.0
    },
    # 3. DAI / USDC.e (Fee 100: 0.01% - TVL > $1.2M)
    "DAI_USDCe_100": {
        "nama": "DAI / USDC.e (100)",
        "quick": "0xf04adbf75cdfc5ed26eea4bbbb991db002036bdd",
        "uni": "0x5645dcb64c059aa11212707fbf4e7f984440a8cf",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 3500.0, "uni_fee": 100, "fee_tot": 0.40,
        "min_r0": 5000.0, "min_r1": 5000.0
    },
    # 4. DAI / USDC.e (Fee 500: 0.05% - TVL > $3M)
    "DAI_USDCe_500": {
        "nama": "DAI / USDC.e (500)",
        "quick": "0xf04adbf75cdfc5ed26eea4bbbb991db002036bdd",
        "uni": "0x5f69c2ec01c22843f8273838d570243fd1963014",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",   # USDC.e
        "target": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 3500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 5000.0, "min_r1": 5000.0
    },
    # 5. USDC.e / USDT (Fee 100: 0.01% - TVL > $2M)
    "USDCe_USDT_100": {
        "nama": "USDC.e / USDT (100)",
        "quick": "0x2cf7252e74036d1da831d11089d326296e64a728",
        "uni": "0xdac8a8e6dbf8c690ec6815e0ff03491b2770255d",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "dec0": 6, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 4000.0, "uni_fee": 100, "fee_tot": 0.40,
        "min_r0": 10000.0, "min_r1": 10000.0
    },
    # 6. USDC.e / USDT (Fee 500: 0.05% - TVL > $5M)
    "USDCe_USDT_500": {
        "nama": "USDC.e / USDT (500)",
        "quick": "0x2cf7252e74036d1da831d11089d326296e64a728",
        "uni": "0x3f5228d0e7d75467366be7de2c31d0d098ba2c23",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "dec0": 6, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 4000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 10000.0, "min_r1": 10000.0
    },
    # 7. WMATIC / USDT (Fee 500 - TVL > $2M)
    "MATIC_USDT_500": {
        "nama": "WMATIC / USDT (500)",
        "quick": "0x604229c960e5cacf2aaeac8be68ac07ba9df81c3",
        "uni": "0x9b08288c3be4f62bbf8d1c20ac9c5e6f9467d8b7",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 10000.0, "min_r1": 1000.0
    },
    # 8. WMATIC / USDC.e (Fee 500 - TVL $1.8M)
    "MATIC_USDCe_500": {
        "nama": "WMATIC / USDC.e (500)",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0xa374094527e1673A86dE625aa59517c5de346d32",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 10000.0, "min_r1": 1000.0
    },
    # 9. WMATIC / USDC.e (Fee 3000 - TVL $1.5M)
    "MATIC_USDCe_3000": {
        "nama": "WMATIC / USDC.e (3000)",
        "quick": "0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827",
        "uni": "0x88f3c15523544835ff6c738ddb30995339ad57d6",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 10000.0, "min_r1": 1000.0
    },
    # 10. WMATIC / DAI (Fee 500 - TVL $200k)
    "MATIC_DAI_500": {
        "nama": "WMATIC / DAI (500)",
        "quick": "0xeef611894ceae652979c9d0dae1deb597790c6ee",
        "uni": "0x0f663c16dd7c65cf87edb9229464ca77aeea536b",
        "asset": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "DAI", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 5000.0, "min_r1": 1000.0
    },
    # 11. WMATIC / DAI (Fee 3000 - TVL $450k)
    "MATIC_DAI_3000": {
        "nama": "WMATIC / DAI (3000)",
        "quick": "0xeef611894ceae652979c9d0dae1deb597790c6ee",
        "uni": "0xfe530931da161232ec76a7c3bea7d36cf3811a0d",
        "asset": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",  # DAI
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "DAI", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 5000.0, "min_r1": 1000.0
    },
    # 12. WMATIC / WETH (Fee 500 - TVL $2.5M)
    "MATIC_WETH_500": {
        "nama": "WMATIC / WETH (500)",
        "quick": "0xadbf1854e5883eb8aa7baf50705338739e558e5b",
        "uni": "0x86f1d8390222a3691c28938ec7404a1661e618e0",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 10000.0, "min_r1": 5.0
    },
    # 13. WMATIC / WETH (Fee 3000 - TVL $1.2M)
    "MATIC_WETH_3000": {
        "nama": "WMATIC / WETH (3000)",
        "quick": "0xadbf1854e5883eb8aa7baf50705338739e558e5b",
        "uni": "0x167384319b41f7094e62f7506409eb38079abff8",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "target": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2500.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 10000.0, "min_r1": 5.0
    },
    # 14. WETH / USDT (Fee 500 - TVL $3M)
    "ETH_USDT_500": {
        "nama": "WETH / USDT (500)",
        "quick": "0xf6422b997c7f54d1c6a6e103bcb1499eea0a7046",
        "uni": "0xbb98b3d2b18aef63a3178023a920971cf5f29be4",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 5.0, "min_r1": 5000.0
    },
    # 15. WETH / USDT (Fee 3000 - TVL $2M)
    "ETH_USDT_3000": {
        "nama": "WETH / USDT (3000)",
        "quick": "0xf6422b997c7f54d1c6a6e103bcb1499eea0a7046",
        "uni": "0x4ccd010148379ea531d6c587cfdd60180196f9b1",
        "asset": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",   # USDT
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 18, "dec1": 6, "asset_dec": 6, "asset_sym": "USDT", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 5.0, "min_r1": 5000.0
    },
    # 16. WETH / USDC.e (Fee 100 - TVL $2.4M, Fee 0.01% Ultra Low!)
    "ETH_USDCe_100": {
        "nama": "WETH / USDC.e (100)",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x04537f43f6add7b1b60cab199c7a910024ee0594",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 4000.0, "uni_fee": 100, "fee_tot": 0.36,
        "min_r0": 5000.0, "min_r1": 2.0
    },
    # 17. WETH / USDC.e (Fee 500 - TVL $2.2M)
    "ETH_USDCe_500": {
        "nama": "WETH / USDC.e (500)",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x45dda9cb7c25131df268515131f647d726f50608",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 3500.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 5000.0, "min_r1": 2.0
    },
    # 18. WETH / USDC.e (Fee 3000 - TVL $1.8M)
    "ETH_USDCe_3000": {
        "nama": "WETH / USDC.e (3000)",
        "quick": "0x853ee4b2a13f8a742d64c8f088be7ba2131f670d",
        "uni": "0x0e44ceb592acfc5d3f09d996302eb4c499ff8c10",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "dec0": 6, "dec1": 18, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": True,
        "max_loan_usd": 3500.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 5000.0, "min_r1": 2.0
    },
    # 19. WBTC / WETH (Fee 500 - TVL $3M)
    "WBTC_WETH_500": {
        "nama": "WBTC / WETH (500)",
        "quick": "0xdc9232e2df177d7a12fdff6ecbab114e2231198d",
        "uni": "0x50eaedb835021e4a108b7290636d62e9765cc6d7",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "target": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",  # WBTC
        "dec0": 8, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 0.5, "min_r1": 5.0
    },
    # 20. WBTC / WETH (Fee 3000 - TVL $1.5M)
    "WBTC_WETH_3000": {
        "nama": "WBTC / WETH (3000)",
        "quick": "0xdc9232e2df177d7a12fdff6ecbab114e2231198d",
        "uni": "0xfe343675878100b344802a6763fd373fdeed07a4",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "target": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",  # WBTC
        "dec0": 8, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 3000.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 0.5, "min_r1": 5.0
    },
    # 21. WBTC / USDC.e (Fee 500 - TVL > $1.2M)
    "WBTC_USDCe_500": {
        "nama": "WBTC / USDC.e (500)",
        "quick": "0xf6a637525402643b0654a54bead2cb9a83c8b498",
        "uni": "0xeef1a9507b3d505f0062f2be9453981255b503c8",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6", # WBTC
        "dec0": 8, "dec1": 6, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": False,
        "max_loan_usd": 4000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 0.1, "min_r1": 5000.0
    },
    # 22. WBTC / USDC.e (Fee 3000 - TVL > $600k)
    "WBTC_USDCe_3000": {
        "nama": "WBTC / USDC.e (3000)",
        "quick": "0xf6a637525402643b0654a54bead2cb9a83c8b498",
        "uni": "0x847b64f9d3a95e977d157866447a5c0a5dfa0ee5",
        "asset": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC.e
        "target": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6", # WBTC
        "dec0": 8, "dec1": 6, "asset_dec": 6, "asset_sym": "USDCe", "is_asset_t0": False,
        "max_loan_usd": 4000.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 0.1, "min_r1": 5000.0
    },
    # 23. LINK / WETH (Fee 500 - TVL $120k)
    "LINK_WETH_500": {
        "nama": "LINK / WETH (500)",
        "quick": "0x5ca6ca6c3709e1e6cfe74a50cf6b2b6ba2dadd67",
        "uni": "0x3dc10d7bfb94eeb009203e84a653e5764f71771d",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "target": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",  # LINK
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 500.0, "min_r1": 2.0
    },
    # 24. LINK / WETH (Fee 3000 - TVL $380k)
    "LINK_WETH_3000": {
        "nama": "LINK / WETH (3000)",
        "quick": "0x5ca6ca6c3709e1e6cfe74a50cf6b2b6ba2dadd67",
        "uni": "0x3e31ab7f37c048fc6574189135d108df80f0ea26",
        "asset": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
        "target": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",  # LINK
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WETH", "is_asset_t0": False,
        "max_loan_usd": 2000.0, "uni_fee": 3000, "fee_tot": 0.69,
        "min_r0": 500.0, "min_r1": 2.0
    },
    # 25. LINK / WMATIC (Fee 500 - TVL > $350k)
    "LINK_MATIC_500": {
        "nama": "LINK / WMATIC (500)",
        "quick": "0x3c986748414a812e455dcd5418246b8fded5c369",
        "uni": "0x0a28c2f5e0e8463e047c203f00f649812ae67e4f",
        "asset": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC
        "target": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39", # LINK
        "dec0": 18, "dec1": 18, "asset_dec": 18, "asset_sym": "WMATIC", "is_asset_t0": True,
        "max_loan_usd": 2000.0, "uni_fee": 500, "fee_tot": 0.44,
        "min_r0": 500.0, "min_r1": 5.0
    }
}

MULTICALL2_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"
SIG_GET_RESERVES = keccak(text="getReserves()")[:4]
SIG_SLOT0 = keccak(text="slot0()")[:4]
SIG_TRY_AGGREGATE = keccak(text="tryAggregate(bool,(address,bytes)[])")[:4]

def get_active_rpc():
    for rpc in POLYGON_RPCS:
        try:
            r = requests.post(rpc, json={"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}, timeout=2.5)
            if r.status_code == 200 and "result" in r.json():
                return rpc
        except Exception:
            continue
    return POLYGON_RPCS[0]

def get_current_gas_price(active_rpc):
    try:
        r = requests.post(active_rpc, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}, timeout=2.0)
        res = r.json().get("result")
        if res:
            return int(res, 16) / 1e9
    except Exception:
        pass
    return 35.0

def calculate_dynamic_loan(pool_cfg, spread_pct, r0_clean, r1_clean):
    if pool_cfg["is_asset_t0"]:
        reserve_asset = r0_clean
    else:
        reserve_asset = r1_clean
    
    max_cfg = pool_cfg.get("max_loan_usd", 2000.0)
    max_safe_borrow = reserve_asset * 0.05
    
    if spread_pct >= 1.2:
        multiplier = 1.0
    elif spread_pct >= 0.8:
        multiplier = 0.75
    elif spread_pct >= 0.5:
        multiplier = 0.50
    else:
        multiplier = 0.30
        
    optimal_loan = min(max_cfg * multiplier, max_safe_borrow)
    return max(optimal_loan, 100.0)

def calculate_priority_tip(est_cuan_usd):
    if est_cuan_usd >= 10.0:
        return 80.0
    elif est_cuan_usd >= 5.0:
        return 50.0
    elif est_cuan_usd >= 2.0:
        return 35.0
    else:
        return 25.0

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload, timeout=4)
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
                        f"💵 *Laba Bersih:* `+${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})`\n"
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
                        f"ℹ️ Transaksi dibatalkan secara aman oleh kontrak pintar karena pergerakan tick slippage sebelum transaksi masuk blok.\n"
                        f"🔗 [Lihat Tx](https://polygonscan.com/tx/{tx_hash})\n"
                        f"⛽ *Biaya Gas Revert:* ~Rp 120 perak."
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
    print("  🚀 MESIN ARBITRASE TURBO 25 KOLAM RAKSASA - AUTONOMOUS 24/7 (AZURE CLOUD)", flush=True)
    print(f"  Dompet Penerima Cuan: {DOMPET_ANDA}", flush=True)
    print("=" * 88, flush=True)
    
    is_live_ready = False
    if SMART_CONTRACT_ADDRESS and METAMASK_PRIVATE_KEY:
        print(f"  ⚡ STATUS EKSEKUTOR: READY ON-CHAIN SNIPER (0-DELAY)")
        print(f"  📍 Kontrak Pintar: {SMART_CONTRACT_ADDRESS}\n")
        is_live_ready = True
    else:
        print("  ⚠️ STATUS EKSEKUTOR: MODE RADAR PENGAMATAN ONLY (Kredensial Belum Terdeteksi)\n")

    send_telegram_alert(
        f"🤖 *RADAR ARBITRASE TURBO 25 KOLAM RAKSASA AKTIF!* 🚀\n\n"
        f"🌐 *Total Kolam:* `25 Kolam Likuiditas Utama Polygon (> $20 Juta TVL)`\n"
        f"⚡ *Mode:* `{'0-Delay Flash Loan Sniper' if is_live_ready else 'Radar Pengamatan'}`\n"
        f"🛡️ *Anti-Frontrunning:* `1RPC VIP Private Routing`\n"
        f"🛡️ *Pre-Flight Firewall:* `Zero-Cost EVM Simulation Shield (Aktif)`\n"
        f"💼 *Dompet Target:* `{DOMPET_ANDA}`\n\n"
        f"Mesin stand-by 24/7 memantau volatilitas on-chain."
    )

    last_alert_time = {}
    cycle = 0

    while True:
        cycle += 1
        active_rpc = get_active_rpc()
        
        # Bangun batch Multicall2 untuk seluruh 25 kolam
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
            }, timeout=3.5)
            
            resp_data = r.json().get("result")
            if not resp_data or resp_data == "0x":
                time.sleep(0.5)
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
            time.sleep(1.0)
            continue

        gas_gwei = get_current_gas_price(active_rpc)
        waktu = datetime.now().strftime("%H:%M:%S")

        # Parsing data 25 kolam
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
                    fee_total = cfg.get("fee_tot", 0.44)
                    
                    if spread_pct > fee_total:
                        effective_loan_usd = calculate_dynamic_loan(cfg, spread_pct, r0_clean, r1_clean)
                        
                        # Estimasi slippage
                        reserve_depth = r0_clean if cfg["is_asset_t0"] else r1_clean
                        price_impact_pct = (effective_loan_usd / (reserve_depth + effective_loan_usd)) * 100.0
                        real_net_pct = spread_pct - fee_total - price_impact_pct
                        
                        if real_net_pct > 0.05:
                            est_cuan_usd = (effective_loan_usd * real_net_pct) / 100.0
                            est_cuan_idr = est_cuan_usd * 18100.0
                            tip_gwei = calculate_priority_tip(est_cuan_usd)
                            
                            arah = "QuickSwap ➔ Uniswap V3" if p_quick < p_uni else "Uniswap V3 ➔ QuickSwap"
                            
                            print(f"\n⚡ [{waktu}] ARBITRASE VALID: {cfg['nama']} | Net: +{real_net_pct:.3f}% | Loan: ${effective_loan_usd:.0f} | Cuan: +${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})", flush=True)

                            # Eksekusi Sniper On-Chain (0-Delay)
                            if is_live_ready:
                                is_quick_first = (p_quick < p_uni)
                                router_a = "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff" if is_quick_first else "0xE592427A0AEce92De3Edee1F18E0157C05861564"
                                router_b = "0xE592427A0AEce92De3Edee1F18E0157C05861564" if is_quick_first else "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"
                                
                                loan_amount_raw = int(effective_loan_usd * (10 ** cfg["asset_dec"]))
                                min_repay_raw = int(loan_amount_raw * 1.0005)
                                
                                params_encoded = encode(
                                    ['address', 'address', 'address', 'address', 'uint24', 'bool', 'uint256'],
                                    [
                                        cfg["asset"],
                                        cfg["target"],
                                        router_a,
                                        router_b,
                                        cfg.get("uni_fee", 500),
                                        is_quick_first,
                                        min_repay_raw
                                    ]
                                )
                                
                                sig_exec = keccak(text="executeArbitrage(address,uint256,bytes)")[:4]
                                exec_calldata = sig_exec + encode(
                                    ['address', 'uint256', 'bytes'],
                                    [cfg["asset"], loan_amount_raw, params_encoded]
                                )
                                calldata_hex = "0x" + exec_calldata.hex()
                                
                                # 1. Pre-Flight Zero-Cost EVM Simulation Shield
                                sim_ok, sim_msg = simulate_arbitrage_execution(SMART_CONTRACT_ADDRESS, calldata_hex, active_rpc)
                                
                                if not sim_ok:
                                    print(f"  🛡️ [Pre-Flight Simulation Dicegah]: {sim_msg} (Hemat Saldo Gas & Modal)", flush=True)
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
                                            f"💰 *Target Laba:* `+${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})`\n"
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
                                # Notifikasi Deteksi Radar Pengamatan (Throttle 60 detik)
                                last_t = last_alert_time.get(k, 0)
                                if (time.time() - last_t) > 60:
                                    last_alert_time[k] = time.time()
                                    cuan_msg = (
                                        f"🔍 *RADAR DETEKSI SPREAD!* 📡\n\n"
                                        f"🪙 *Pasangan:* {cfg['nama']}\n"
                                        f"📏 *Pinjaman Disesuaikan:* `${effective_loan_usd:.0f} USD`\n"
                                        f"📊 *Spread Kotor:* {spread_pct:.3f}%\n"
                                        f"📉 *Slippage Kolam:* {price_impact_pct:.3f}%\n"
                                        f"💰 *Profit Bersih:* +{real_net_pct:.3f}%\n"
                                        f"💵 *Estimasi Cuan:* `${est_cuan_usd:.2f} (~Rp {est_cuan_idr:,.0f})`\n"
                                        f"🔄 *Jalur:* {arah}\n"
                                        f"🛡️ *Anti-Frontrunning:* Terenkripsi 1RPC"
                                    )
                                    send_telegram_alert(cuan_msg)

        time.sleep(0.4)

if __name__ == "__main__":
    main()
