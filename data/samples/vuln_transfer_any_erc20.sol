// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title LiquidityPoolManager
 * @dev VULNERABLE CONTRACT: The rescue helper `transferAnyERC20Token` is public
 * and allows any caller to drain arbitrary ERC20 tokens locked inside this contract.
 */
contract LiquidityPoolManager {
    address public admin;
    uint256 public totalLiquidity;

    event AdminChanged(address indexed oldAdmin, address indexed newAdmin);
    event RescuedTokens(address indexed token, address indexed to, uint256 amount);

    constructor() {
        admin = msg.sender;
    }

    /**
     * @dev ASTRO Target Function: Missing Access Control Guard!
     * Lacks `onlyAdmin` or `msg.sender == admin` check before executing external transfer.
     */
    function transferAnyERC20Token(address tokenAddress, address to, uint256 amount) public returns (bool success) {
        success = IERC20(tokenAddress).transfer(to, amount);
        emit RescuedTokens(tokenAddress, to, amount);
        return success;
    }

    function setAdmin(address newAdmin) external {
        require(msg.sender == admin, "Only admin");
        admin = newAdmin;
        emit AdminChanged(msg.sender, newAdmin);
    }
}
