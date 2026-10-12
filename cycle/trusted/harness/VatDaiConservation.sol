// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

// PRE-FIXED focused harness (TRUSTED) for the Maker invariant `Σ dai[u] == debt`
// on DSS Vat. The full Vat is intractable for SMTChecker (complexity wall), so this
// is a SOUND OVER-APPROXIMATION of Vat's dai/debt subsystem:
//   * every dai-mutating op (frob/fold/heal/suck/move) with its EXACT Vat deltas;
//   * `dtab` (= rate·dart, the nonlinear ray-mul) is HAVOC'd to an arbitrary signed
//     delta — sound because Σdai==debt does not depend on its value (it lands in
//     BOTH dai[w] and debt symmetrically, so the nonlinearity cancels);
//   * irrelevant state/guards (ink/art/gem/safety requires) omitted → strictly MORE
//     reachable states. Invariant holding here ⇒ holding in real Vat (a subset).
// `ghostDaiSum` shadows Σ dai[u] (CVL-hook-style; faithfulness is the modelling step).
contract VatDaiConservation {
    mapping(address => uint256) public dai; // [rad]
    uint256 public debt;                    // [rad]
    uint256 public ghostDaiSum;             // shadow of Σ dai[u]

    // --- Math ---
    // Vat applies a signed delta via `_add(uint,int)` = `unchecked{x+uint(y)};require(...)`
    // — the two's-complement reinterpret of a negative int as a huge uint defeats CHC
    // (the SMTChecker wall, even for this trivially-inductive invariant). `_applyDelta`
    // re-expresses the SAME function (same result, same revert-on-bound) branch-wise, so
    // z3/CHC can reason about it. Sound: identical semantics to `_add(uint,int)`.
    function _applyDelta(uint256 x, int256 y) internal pure returns (uint256) {
        if (y >= 0) return x + uint256(y);   // reverts on overflow (== Vat's z<=x check)
        else return x - uint256(-y);          // reverts on underflow (== Vat's z>=x check)
    }
    function _add(uint256 x, uint256 y) internal pure returns (uint256 z) {
        unchecked { require((z = x + y) >= x); }
    }
    function _sub(uint256 x, uint256 y) internal pure returns (uint256 z) {
        unchecked { require((z = x - y) <= x); }
    }

    // dtab = rate·dart is the GHOST (havoc'd): exact value irrelevant to dai-conservation.
    function frob(address w, int256 dtab) external {
        dai[w]      = _applyDelta(dai[w],      dtab);
        debt        = _applyDelta(debt,        dtab);
        ghostDaiSum = _applyDelta(ghostDaiSum, dtab); // hook: dai[w] +dtab ⇒ Σdai +dtab
    }
    function fold(address u, int256 rad) external {
        dai[u]      = _applyDelta(dai[u],      rad);
        debt        = _applyDelta(debt,        rad);
        ghostDaiSum = _applyDelta(ghostDaiSum, rad);
    }
    function suck(address v, uint256 rad) external {
        dai[v]      = _add(dai[v],      rad);
        debt        = _add(debt,        rad);
        ghostDaiSum = _add(ghostDaiSum, rad);
    }
    function heal(uint256 rad) external {
        dai[msg.sender] = _sub(dai[msg.sender], rad);
        debt            = _sub(debt,            rad);
        ghostDaiSum     = _sub(ghostDaiSum,     rad);
    }
    function move(address src, address dst, uint256 rad) external {
        dai[src] = _sub(dai[src], rad);
        dai[dst] = _add(dai[dst], rad);
        // debt unchanged; Σdai unchanged (−rad +rad) ⇒ ghostDaiSum untouched
    }

    function __check() public view {
        assert(ghostDaiSum == debt); // __INVARIANT__ (gateway overwrites the expr)
    }
}
