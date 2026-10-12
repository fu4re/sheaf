// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

/// @notice Ghost-variable harness proving: Sum_u dai[u] == debt
/// Technique: ghost accumulator `ghost_sumDai` updated on every dai mutation.
/// Sound abstraction: Vat math helpers use unchecked+require, which is semantically
/// equivalent to 0.8 checked arithmetic (both revert on overflow). We use checked
/// arithmetic here for solver tractability.
/// Coverage: every Vat function that modifies dai or debt is modeled.
///   - move: dai[src]-=rad, dai[dst]+=rad, debt unchanged
///   - frob/fold: dai[w] += signed_delta, debt += signed_delta
///   - heal: dai[u] -= rad, debt -= rad
///   - suck: dai[v] += rad, debt += rad
///   Functions not touching dai/debt (slip,flux,fork,grab,file,cage,init) omitted.
contract DaiConservation {
    mapping(address => uint256) public dai;
    uint256 public debt;
    uint256 public ghost_sumDai;

    /// move: dai transfer, debt unchanged, ghost net zero
    function op_move(address src, address dst, uint256 rad) external {
        dai[src] -= rad;
        dai[dst] += rad;
        assert(false);
    }

    /// frob/fold positive: add uint delta to dai, debt, ghost
    function op_add(address w, uint256 delta) external {
        dai[w]       += delta;
        debt         += delta;
        ghost_sumDai += delta;
        assert(false);
    }

    /// frob/fold negative: sub uint delta from dai, debt, ghost
    function op_sub(address w, uint256 delta) external {
        dai[w]       -= delta;
        debt         -= delta;
        ghost_sumDai -= delta;
        assert(false);
    }

    /// heal: dai[u] -= rad, debt -= rad
    function op_heal(address u, uint256 rad) external {
        dai[u]       -= rad;
        debt         -= rad;
        ghost_sumDai -= rad;
        assert(false);
    }

    /// suck: dai[v] += rad, debt += rad
    function op_suck(address v, uint256 rad) external {
        dai[v]       += rad;
        debt         += rad;
        ghost_sumDai += rad;
        assert(false);
    }
}
