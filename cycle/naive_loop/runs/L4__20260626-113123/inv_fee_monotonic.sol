// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

/// @notice 2-state snapshot harness proving: fold with non-negative rate delta
/// never decreases debt.
/// Technique: pre-state snapshot of debt; assert debt_new >= debt_old after fold.
/// Sound abstraction: fold logic is verbatim from Vat; Art/rate/debt/dai can reach
/// any values via abstract setters (over-approximation of frob/grab/suck/heal/init).
contract FeeMonotonic {
    uint256 public Art;
    uint256 public ilk_rate;
    uint256 public debt;
    mapping(address => uint256) public dai;

    // --- Vat math (verbatim) ---
    function _add(uint x, int y) internal pure returns (uint z) {
        unchecked { z = x + uint(y); require(y >= 0 || z <= x); require(y <= 0 || z >= x); }
    }
    function _add(uint x, uint y) internal pure returns (uint z) {
        unchecked { require((z = x + y) >= x); }
    }
    function _mul(uint x, int y) internal pure returns (int z) {
        unchecked { z = int(x) * y; require(int(x) >= 0); require(y == 0 || z / y == int(x)); }
    }

    /// Allow solver to explore arbitrary reachable states.
    function set_Art(uint256 a) external { Art = a; }
    function set_rate(uint256 r) external { ilk_rate = r; }
    function set_debt(uint256 d) external { debt = d; }
    function set_dai(address u, uint256 v) external { dai[u] = v; }

    /// Fold with non-negative rate delta: debt must not decrease.
    /// Verbatim fold logic from Vat (minus auth/live checks, which are orthogonal).
    function fold(address u, int rate_delta) external {
        require(rate_delta >= 0);
        uint256 debt_old = debt;

        ilk_rate = _add(ilk_rate, rate_delta);
        int rad  = _mul(Art, rate_delta);
        dai[u]   = _add(dai[u], rad);
        debt     = _add(debt,   rad);

        assert(debt >= debt_old);
    }
}
