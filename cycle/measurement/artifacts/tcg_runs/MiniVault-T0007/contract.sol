// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Tier-1 mocked vault — SUT (system under test) for the pipeline slice.
/// "Pre-understood": 1:1 share<->asset backing, so the economic conservation
/// law `totalShares == totalAssets` provably holds (the known-GOOD case).
///
/// Slice 1 keeps the arithmetic LINEAR on purpose: it isolates the trust-line
/// separation (agent proposes invariant -> gateway -> solver) from the
/// nonlinear-`mulDiv` ghost-abstraction wall (T-04), which Slice 2 introduces.
///
/// The overflow обвязка below is part of the PRE-FIXED trusted harness, not
/// agent-generated (see ../trusted/harness/ghost.md).
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
