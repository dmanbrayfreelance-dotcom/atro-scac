// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SafeOwnableVault
 * @dev PROTECTED CONTRACT: Proper access control implemented using the `onlyOwner`
 * modifier and explicit sender checks on sensitive administrative functions.
 */
contract SafeOwnableVault {
    address public owner;
    bool public paused;
    uint256 public protocolFee;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event FeeUpdated(uint256 newFee);
    event Paused(bool isPaused);

    modifier onlyOwner() {
        require(msg.sender == owner, "Ownable: caller is not the owner");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "Pausable: paused");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Ownable: new owner is the zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function withdraw(uint256 amount) public onlyOwner {
        require(amount <= address(this).balance, "Insufficient balance");
        payable(owner).transfer(amount);
    }

    function setFee(uint256 _fee) external onlyOwner {
        require(_fee <= 1000, "Fee too high");
        protocolFee = _fee;
        emit FeeUpdated(_fee);
    }

    function pause() public onlyOwner {
        paused = true;
        emit Paused(true);
    }
}
