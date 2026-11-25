// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title StakingTreasury
 * @dev VULNERABLE CONTRACT: The `withdraw` function allows any caller to withdraw funds
 * from the treasury contract without verifying ownership or caller authorization.
 */
contract StakingTreasury {
    address public owner;
    uint256 public totalReserve;

    event Deposit(address indexed sender, uint256 amount);
    event Withdrawal(address indexed recipient, uint256 amount);

    constructor() payable {
        owner = msg.sender;
        totalReserve = msg.value;
    }

    receive() external payable {
        totalReserve += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    /**
     * @dev ASTRO Target Function: Missing Access Control Guard!
     * Lacks `onlyOwner` or `msg.sender == owner` check.
     */
    function withdraw(uint256 amount) public {
        require(amount <= address(this).balance, "Insufficient balance");
        totalReserve -= amount;
        payable(msg.sender).transfer(amount);
        emit Withdrawal(msg.sender, amount);
    }

    function setOwner(address newOwner) external {
        require(msg.sender == owner, "Caller is not owner");
        owner = newOwner;
    }
}
