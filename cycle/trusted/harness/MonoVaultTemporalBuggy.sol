// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ===== BUGGY SUT (inlined): `accrue` can OVERWRITE fees, allowing a decrease =====
contract MonoVaultBuggy {
    uint256 public accumulatedFees;

    function accrue(uint256 newFees) public {
        require(newFees <= type(uint128).max, "new cap");
        accumulatedFees = newFees; // BUG: assignment, not +=, so fees can drop
    }
}

/// Temporal harness over the buggy SUT: monotonicity must be REFUTED (witness:
/// old fees high, newFees lower).
contract __Harness is MonoVaultBuggy {
    function __check_temporal(uint256 newFees) public {
        uint256 old_accumulatedFees = accumulatedFees;
        accrue(newFees);
        assert(accumulatedFees >= old_accumulatedFees); // __INVARIANT__
    }
}
