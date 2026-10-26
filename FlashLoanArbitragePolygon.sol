// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FlashLoanArbitragePolygon
 * @notice Kontrak Arbitrase Flash Loan Aave V3 di Jaringan Polygon (PoS)
 * @dev Menggunakan Aave V3 PoolAddressesProvider di Polygon: 0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb
 */

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
}

interface IFlashLoanSimpleReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

interface IPool {
    function flashLoanSimple(
        address receiverAddress,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

interface IUniswapV2Router {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}

contract FlashLoanArbitragePolygon is IFlashLoanSimpleReceiver {
    address public immutable owner;
    IPool public immutable aavePool;

    event FlashLoanExecuted(address asset, uint256 amount, uint256 profit);

    modifier onlyOwner() {
        require(msg.sender == owner, "Hanya pemilik kontrak!");
        _;
    }

    constructor(address _aavePoolAddress) {
        owner = msg.sender;
        aavePool = IPool(_aavePoolAddress);
    }

    function requestFlashLoan(
        address asset,
        uint256 amount,
        bytes calldata params
    ) external onlyOwner {
        aavePool.flashLoanSimple(
            address(this),
            asset,
            amount,
            params,
            0
        );
    }

    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        require(msg.sender == address(aavePool), "Hanya Aave!");
        require(initiator == address(this), "Hanya kontrak ini!");

        (address routerBeli, address routerJual, address targetToken) = abi.decode(
            params,
            (address, address, address)
        );

        // 1. Eksekusi Pembelian di Bursa 1
        {
            IERC20(asset).approve(routerBeli, amount);
            address[] memory pathBeli = new address[](2);
            pathBeli[0] = asset;
            pathBeli[1] = targetToken;
            IUniswapV2Router(routerBeli).swapExactTokensForTokens(
                amount,
                0,
                pathBeli,
                address(this),
                block.timestamp + 60
            );
        }

        // 2. Eksekusi Penjualan di Bursa 2
        {
            uint256 targetBalance = IERC20(targetToken).balanceOf(address(this));
            IERC20(targetToken).approve(routerJual, targetBalance);
            address[] memory pathJual = new address[](2);
            pathJual[0] = targetToken;
            pathJual[1] = asset;
            IUniswapV2Router(routerJual).swapExactTokensForTokens(
                targetBalance,
                0,
                pathJual,
                address(this),
                block.timestamp + 60
            );
        }

        // 3. Verifikasi Keuntungan & Bayar Pinjaman
        uint256 currentBalance = IERC20(asset).balanceOf(address(this));
        uint256 totalDebt = amount + premium;
        require(currentBalance > totalDebt, "Tidak profit, revert!");

        uint256 profit = currentBalance - totalDebt;
        if (profit > 0) {
            IERC20(asset).transfer(owner, profit);
            emit FlashLoanExecuted(asset, amount, profit);
        }

        // Izinkan Aave menarik kembali pinjaman pokok + fee
        IERC20(asset).approve(address(aavePool), totalDebt);

        return true;
    }

    function withdrawToken(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) {
            IERC20(token).transfer(owner, bal);
        }
    }
}
