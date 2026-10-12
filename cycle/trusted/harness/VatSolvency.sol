// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

// PRE-FIXED focused harness (TRUSTED) for the Maker SOLVENCY invariant
//   debt == vice + Σ_i (ilks[i].Art · ilks[i].rate)
// (single-ilk core: debt == vice + Art·rate). The nonlinear product `Art·rate` is
// intractable for the solver, so it is shadowed by `ghostAR` — a scalar tracking
// Σ(Art·rate), updated by the SAME product-delta the real accounting applies:
//   frob: Δ(Art·rate) = rate·dart = dtab      grab: Δ(Art·rate) = rate·dart = dtab
//   fold: Δ(Art·rate) = Art·Δrate = rad
// `dtab`/`rad` are GHOSTS (havoc'd): the conservation relation does not depend on
// their value (they land symmetrically in debt and ghostAR), so the solver proves
// `debt == vice + ghostAR` linearly.
//
// FAITHFULNESS of the shadow (`ghostAR == Σ Art·rate`) rests on the product-delta
// identity (Art+dart)·rate == Art·rate + dart·rate — i.e. distributivity — which is
// machine-proven in Lean (`AaveArith.ar_delta`, see ../proofs/axiom_registry.json).
// The trusted base for this shadow is thus a PROVEN theorem, not an axiom-on-faith.
contract VatSolvency {
    uint256 public debt;    // [rad]
    uint256 public vice;    // [rad]
    uint256 public ghostAR; // shadow of Σ_i (Art_i · rate_i) [rad]

    function _applyDelta(uint256 x, int256 y) internal pure returns (uint256) {
        if (y >= 0) return x + uint256(y);
        else return x - uint256(-y);
    }
    function _add(uint256 x, uint256 y) internal pure returns (uint256 z) {
        unchecked { require((z = x + y) >= x); }
    }
    function _sub(uint256 x, uint256 y) internal pure returns (uint256 z) {
        unchecked { require((z = x - y) <= x); }
    }

    // frob: Art += dart ⇒ Δ(Art·rate) = dtab ; debt += dtab ; vice unchanged
    function frob(int256 dtab) external {
        debt    = _applyDelta(debt,    dtab);
        ghostAR = _applyDelta(ghostAR, dtab);
    }
    // fold: rate += Δrate ⇒ Δ(Art·rate) = rad ; debt += rad ; vice unchanged
    function fold(int256 rad) external {
        debt    = _applyDelta(debt,    rad);
        ghostAR = _applyDelta(ghostAR, rad);
    }
    // grab: Art += dart ⇒ ghostAR += dtab ; vice -= dtab ; debt unchanged
    function grab(int256 dtab) external {
        ghostAR = _applyDelta(ghostAR, dtab);
        vice    = _applyDelta(vice,    -dtab);
    }
    // suck: debt += rad ; vice += rad ; ghostAR unchanged
    function suck(uint256 rad) external {
        debt = _add(debt, rad);
        vice = _add(vice, rad);
    }
    // heal: debt -= rad ; vice -= rad ; ghostAR unchanged
    function heal(uint256 rad) external {
        debt = _sub(debt, rad);
        vice = _sub(vice, rad);
    }

    function __check() public view {
        assert(debt == vice + ghostAR); // __INVARIANT__ (gateway overwrites the expr)
    }
}
