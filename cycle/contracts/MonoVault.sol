// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Reference SUT for the TEMPORAL / 2-state invariant class: accrued fees may only
/// grow. The law `accumulatedFees` monotonically non-decreasing relates the state
/// BEFORE and AFTER a call — inexpressible as a single-state invariant. This is
/// exactly Finding-0001's missed `accrueYieldCheck` (fees only increase).
contract MonoVault {
    uint256 public accumulatedFees;

    function accrue(uint256 newFees) public {
        require(accumulatedFees <= type(uint128).max, "fee cap");
        require(newFees <= type(uint128).max, "new cap");
        accumulatedFees += newFees; // monotonic: only grows
    }
}
