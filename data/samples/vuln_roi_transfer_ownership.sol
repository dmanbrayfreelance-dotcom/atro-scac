// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title HighYieldROIInvestment
 * @dev VULNERABLE CONTRACT: The function `transferOwnership` is declared public
 * without any access control modifier (such as `onlyOwner`) or `msg.sender == owner` check.
 * Anyone can invoke this function to hijack ownership and claim protocol fees.
 */
contract HighYieldROIInvestment {
    address public owner;
    uint256 public totalInvested;
    uint256 public dailyRoiBasisPoints = 150; // 1.5% daily
    mapping(address => uint256) public deposits;
    mapping(address => uint256) public lastClaimTime;

    event Invested(address indexed investor, uint256 amount);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        owner = msg.sender;
    }

    function invest() external payable {
        require(msg.value > 0, "Zero deposit");
        deposits[msg.sender] += msg.value;
        totalInvested += msg.value;
        lastClaimTime[msg.sender] = block.timestamp;
        emit Invested(msg.sender, msg.value);
    }

    /**
     * @dev ASTRO Target Function: Missing Access Control Guard!
     * Notice: There is no `require(msg.sender == owner)` or `onlyOwner` modifier.
     */
    function transferOwnership(address newOwner) public {
        require(newOwner != address(0), "Invalid new owner");
        owner = newOwner;
        emit OwnershipTransferred(msg.sender, newOwner);
    }

    function claimRewards() external {
        uint256 elapsed = block.timestamp - lastClaimTime[msg.sender];
        require(elapsed > 0, "Too early");
        uint256 reward = (deposits[msg.sender] * dailyRoiBasisPoints * elapsed) / (10000 * 1 days);
        lastClaimTime[msg.sender] = block.timestamp;
        payable(msg.sender).transfer(reward);
    }
}
