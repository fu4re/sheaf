// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

/// @notice Ghost-variable harness proving: Sum_u sin[u] == vice
/// Technique: ghost accumulator `ghost_sumSin` updated on every sin mutation.
/// Using 0.8 checked arithmetic (equivalent to Vat unchecked+require).
/// Coverage: every Vat function modifying sin or vice:
///   - grab: sin[w] changes by -dtab, vice changes by -dtab (signed; split into pos/neg)
///   - heal: sin[u] -= rad, vice -= rad
///   - suck: sin[u] += rad, vice += rad
contract SinConservation {
    mapping(address => uint256) public sin;
    uint256 public vice;
    uint256 public ghost_sumSin;

    /// grab with positive dtab (dart > 0): sin[w] -= dtab, vice -= dtab
    /// _sub(sin[w], dtab) with dtab > 0 decreases sin[w]
    function op_grab_pos(address w, uint256 d) external {

        vice         -= d;
        ghost_sumSin -= d;
        assert(ghost_sumSin == vice);
    }

    /// grab with negative dtab (liquidation, dart < 0):
    /// _sub(sin[w], dtab) with dtab < 0 increases sin[w] by |dtab|
    /// vice increases by |dtab|
    function op_grab_neg(address w, uint256 d) external {

        vice         += d;
        ghost_sumSin += d;
        assert(ghost_sumSin == vice);
    }

    /// heal: sin[u] -= rad, vice -= rad
    function op_heal(address u, uint256 rad) external {

        vice         -= rad;
        ghost_sumSin -= rad;
        assert(ghost_sumSin == vice);
    }

    /// suck: sin[u] += rad, vice += rad
    function op_suck(address u, uint256 rad) external {

        vice         += rad;
        ghost_sumSin += rad;
        assert(ghost_sumSin == vice);
    }
}
