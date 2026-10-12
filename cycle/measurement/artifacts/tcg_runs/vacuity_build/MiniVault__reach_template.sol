// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

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

contract __ReachHarness is MiniVault {
    function __check_invariant() public view {
        assert(totalShares == totalAssets); // __INVARIANT__ (reachability probe injects false)
    }
}
