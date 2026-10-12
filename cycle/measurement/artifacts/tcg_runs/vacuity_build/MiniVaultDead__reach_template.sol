// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MiniVaultDead {
    uint256 public totalAssets;
    uint256 public totalShares;

    constructor() {
        require(false, "dead: cannot construct");
    }

    function deposit(uint256 assets) public {
        require(assets <= type(uint128).max, "assets too large");
        totalAssets += assets;
        totalShares += assets;
    }
}

contract __ReachHarness is MiniVaultDead {
    function __check_invariant() public view {
        assert(totalShares == totalAssets); // __INVARIANT__ (reachability probe injects false)
    }
}
