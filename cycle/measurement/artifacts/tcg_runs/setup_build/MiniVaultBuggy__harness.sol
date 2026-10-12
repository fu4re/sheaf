// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ===== SUT (inlined verbatim from MiniVaultBuggy.sol) =====
contract MiniVaultBuggy {
    uint256 public totalAssets;
    uint256 public totalShares;

    function deposit(uint256 assets) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(totalShares <= type(uint128).max, "shares cap");

        uint256 mintedShares = assets + 1; // BUG: mints one unbacked share

        totalAssets += assets;
        totalShares += mintedShares;
    }
}

// ===== Generated harness (gateway [4]) =====
// Economic invariant proposed by module [1] (UNTRUSTED), discharged over all
// reachable states by the solver core [5]. Scaffolding is trusted & pre-fixed.
contract __Harness is MiniVaultBuggy {
    function __check_invariant() public view {
        assert(totalShares == totalAssets);
    }
}
