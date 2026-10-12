// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// DELIBERATELY-VACUOUS FIXTURE (T1 vacuity-gate self-test) — the canonical
/// ANTECEDENT-FAILURE trap (Beer/Ben-David/Eisner, IBM Haifa 2001). The invariant
/// sits behind an unsatisfiable guard `require(false)`, so its program point is
/// UNREACHABLE and ANY property there — including the real solvency law — proves
/// VACUOUSLY. Probe R MUST flag it: substituting the invariant with `false` still
/// PROVES (the point is dead), which is the unreachability certificate.
///
/// Single-assert by construction, to avoid the harness-level-OR caveat a 2-leg
/// deposit+withdraw harness would introduce (run_solver matches "violation happens"
/// before "proved safe", so a live leg could mask a dead one).
contract VaultAssetAGDead {
    uint256 public totalAssets;
    uint256 public vaultBal;

    function deposit(uint256 assets) public {
        require(false, "dead guard"); // unsatisfiable antecedent ⇒ dead code below
        vaultBal    += assets;
        totalAssets += assets;
        assert(vaultBal >= totalAssets); // __INVARIANT__ (unreachable ⇒ vacuous)
    }
}
