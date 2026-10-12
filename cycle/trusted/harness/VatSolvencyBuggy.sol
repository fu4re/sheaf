// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

// BUGGY variant: `mintUnbacked` increases debt WITHOUT backing it (no vice, no
// Art·rate) — breaking solvency `debt == vice + Σ(Art·rate)`. The solver must
// REFUTE it: Dai created with neither a CDP nor a system-debt entry.
contract VatSolvencyBuggy {
    uint256 public debt;
    uint256 public vice;
    uint256 public ghostAR;

    function _add(uint256 x, uint256 y) internal pure returns (uint256 z) {
        unchecked { require((z = x + y) >= x); }
    }

    function suck(uint256 rad) external {
        debt = _add(debt, rad);
        vice = _add(vice, rad);
    }
    function mintUnbacked(uint256 rad) external {
        debt = _add(debt, rad); // BUG: debt grows, neither vice nor Art·rate does
    }

    function __check() public view {
        assert(debt == vice + ghostAR); // __INVARIANT__
    }
}
