// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ===== SUT (inlined verbatim from contract.sol) =====
contract ProportionalVault {
    uint256 public totalAssets;
    uint256 public totalShares;

    function deposit(uint256 assets) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(totalShares <= type(uint128).max, "shares cap");

        uint256 mintedShares;
        if (totalShares == 0) {
            mintedShares = assets; // bootstrap 1:1
        } else {
            require(totalAssets > 0, "no assets to price against");
            mintedShares = assets * totalShares / totalAssets; // NONLINEAR
        }

        totalAssets += assets;
        totalShares += mintedShares;
    }
}

// ===== Generated harness (gateway [4]) =====
// Economic invariant proposed by module [1] (UNTRUSTED), discharged over all
// reachable states by the solver core [5]. Scaffolding is trusted & pre-fixed.
contract __Harness is ProportionalVault {
    function __check_invariant() public view {
        assert(totalShares <= totalAssets);
    }
}
