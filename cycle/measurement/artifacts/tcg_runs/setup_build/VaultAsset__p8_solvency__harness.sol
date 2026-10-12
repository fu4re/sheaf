// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address who) external view returns (uint256);
}

contract VaultAsset {
    IERC20  public asset;
    uint256 public totalAssets;

    constructor(IERC20 _asset) {
        asset = _asset;
    }

    function deposit(uint256 assets) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        asset.transferFrom(msg.sender, address(this), assets); // EXTERNAL CALL to B
        totalAssets += assets;
    }

    function withdraw(uint256 assets) public {
        require(assets <= totalAssets, "insufficient");
        totalAssets -= assets;
        asset.transfer(msg.sender, assets); // EXTERNAL CALL to B
    }
}

contract __Harness is VaultAsset {
    constructor(IERC20 a) VaultAsset(a) {}
    // Cross-contract solvency — provable ONLY by reasoning THROUGH the external
    // ERC20 call, which `untrusted` ext-calls havoc as a reentrant callback.
    function __check_solvency() public view {
        assert(asset.balanceOf(address(this)) >= totalAssets);
    }
}
