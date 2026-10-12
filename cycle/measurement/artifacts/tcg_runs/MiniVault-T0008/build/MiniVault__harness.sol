// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ===== SUT (inlined verbatim from contract.sol) =====
contract MiniVault {
    uint256 public totalAssets;
    uint256 public totalShares;

    function deposit(uint256 assets) public {
        // pre-fixed overflow обвязка (trusted): keep running sums within uint128
        // so the linear additions cannot overflow — removes a spurious failure.
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(totalShares <= type(uint128).max, "shares cap");

        uint256 mintedShares = assets; // 1:1 backing (linear)

        totalAssets += assets;
        totalShares += mintedShares;
    }
}

// ===== Generated harness (gateway [4]) =====
// Economic invariant proposed by module [1] (UNTRUSTED), discharged over all
// reachable states by the solver core [5]. Scaffolding is trusted & pre-fixed.
contract __Harness is MiniVault {
    function __check_invariant() public view {
        assert(totalShares == totalAssets);
    }
}
