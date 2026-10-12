// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ===== SUT (inlined) =====
contract MonoVault {
    uint256 public accumulatedFees;

    function accrue(uint256 newFees) public {
        require(accumulatedFees <= type(uint128).max, "fee cap");
        require(newFees <= type(uint128).max, "new cap");
        accumulatedFees += newFees;
    }
}

/// PRE-FIXED temporal harness (TRUSTED) — 2-state / `old()` invariant class.
/// Snapshots the pre-state, runs the method, asserts the relation between old and
/// new state. The agent's `accumulatedFees >= old(accumulatedFees)` lowers to a
/// reference to the snapshot `old_accumulatedFees`. The solver discharges it over
/// all reachable pre-states.
contract __Harness is MonoVault {
    function __check_temporal(uint256 newFees) public {
        uint256 old_accumulatedFees = accumulatedFees; // snapshot = old(...)
        accrue(newFees);
        assert(accumulatedFees >= old_accumulatedFees); // __INVARIANT__ (gateway overwrites)
    }
}
