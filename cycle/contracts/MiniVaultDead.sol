// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Deliberately-vacuous SUT: the constructor reverts, so NO state is reachable and
/// any invariant holds vacuously. The vacuity gate's Probe R must FLAG this.
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
