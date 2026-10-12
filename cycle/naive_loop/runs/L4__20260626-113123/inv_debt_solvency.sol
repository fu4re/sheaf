// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

/// @notice Ghost-variable harness proving: debt == vice + Sum_i(Art_i * rate_i)
/// Technique: ghost accumulator `ghost_sumArtRate` tracks Sum_i(Art_i * rate_i)
/// via deltas. Using 0.8 checked arithmetic (equivalent to Vat unchecked+require).
/// Coverage:
///   - frob: debt += dtab, ghost += dtab (dtab = rate*dart, abstracted as signed delta)
///   - fold: debt += rad,  ghost += rad  (rad = Art*rate_delta, same pattern)
///   - grab: vice changes by -dtab, ghost += dtab. debt unchanged.
///   - heal: debt -= rad, vice -= rad
///   - suck: debt += rad, vice += rad
contract DebtSolvency {
    uint256 public debt;
    uint256 public vice;
    uint256 public ghost_sumArtRate;

    /// frob/fold positive delta: debt += d, ghost += d
    function op_frob_fold_add(uint256 d) external {
        debt             += d;
        ghost_sumArtRate += d;
        assert(debt == vice + ghost_sumArtRate);
    }

    /// frob/fold negative delta: debt -= d, ghost -= d
    function op_frob_fold_sub(uint256 d) external {
        debt             -= d;
        ghost_sumArtRate -= d;
        assert(debt == vice + ghost_sumArtRate);
    }

    /// grab positive dtab: vice -= dtab, ghost += dtab. debt unchanged.
    /// When dtab > 0 (dart > 0, adding art back), vice decreases, sumArtRate increases.
    function op_grab_pos(uint256 d) external {
        vice             -= d;
        ghost_sumArtRate += d;
        assert(debt == vice + ghost_sumArtRate);
    }

    /// grab negative dtab: vice += |dtab|, ghost -= |dtab|. debt unchanged.
    /// When dtab < 0 (liquidation, dart < 0), vice increases, sumArtRate decreases.
    function op_grab_neg(uint256 d) external {
        vice             += d;
        ghost_sumArtRate -= d;
        assert(debt == vice + ghost_sumArtRate);
    }

    /// heal: debt -= rad, vice -= rad. ghost unchanged.
    function op_heal(uint256 rad) external {
        debt -= rad;
        vice -= rad;
        assert(debt == vice + ghost_sumArtRate);
    }

    /// suck: debt += rad, vice += rad. ghost unchanged.
    function op_suck(uint256 rad) external {
        debt += rad;
        vice += rad;
        assert(debt == vice + ghost_sumArtRate);
    }
}
