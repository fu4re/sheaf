// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ===== SUT (inlined verbatim from contract.sol) =====
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

// ===== Generated harness (gateway [4]) =====
// Economic invariant proposed by module [1] (UNTRUSTED), discharged over all
// reachable states by the solver core [5]. Scaffolding is trusted & pre-fixed.
contract __Harness is MiniVaultDead {
    function __check_invariant() public view {
        assert(totalShares == totalAssets);
    }
}
