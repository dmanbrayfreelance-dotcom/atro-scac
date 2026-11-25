// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SafeAccessControlToken
 * @dev PROTECTED CONTRACT: Uses Role-Based Access Control (RBAC) to guard
 * sensitive administrative capabilities including token minting and role assignment.
 */
contract SafeAccessControlToken {
    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    string public name = "SecureGovernanceToken";
    string public symbol = "SGT";
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(bytes32 => mapping(address => bool)) private _roles;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);

    modifier onlyRole(bytes32 role) {
        require(hasRole(role, msg.sender), "AccessControl: sender must have role");
        _;
    }

    constructor() {
        _roles[DEFAULT_ADMIN_ROLE][msg.sender] = true;
        _roles[MINTER_ROLE][msg.sender] = true;
    }

    function hasRole(bytes32 role, address account) public view returns (bool) {
        return _roles[role][account];
    }

    function mint(address to, uint256 amount) public onlyRole(MINTER_ROLE) {
        require(to != address(0), "ERC20: mint to the zero address");
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function setRole(bytes32 role, address account) public onlyRole(DEFAULT_ADMIN_ROLE) {
        require(account != address(0), "Invalid account");
        _roles[role][account] = true;
        emit RoleGranted(role, account, msg.sender);
    }
}
