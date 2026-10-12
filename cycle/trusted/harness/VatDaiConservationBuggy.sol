// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

// BUGGY variant: `mintUnbacked` credits dai (and the shadow sum) WITHOUT increasing
// debt — breaking `Σ dai == debt`. The solver must REFUTE it (the tracked-sum ghost
// is not vacuous; a real dai/debt accounting bug is caught).
contract VatDaiConservationBuggy {
    mapping(address => uint256) public dai;
    uint256 public debt;
    uint256 public ghostDaiSum;

    function _add(uint256 x, uint256 y) internal pure returns (uint256 z) {
        unchecked { require((z = x + y) >= x); }
    }

    function suck(address v, uint256 rad) external {
        dai[v]      = _add(dai[v],      rad);
        debt        = _add(debt,        rad);
        ghostDaiSum = _add(ghostDaiSum, rad);
    }

    function mintUnbacked(address v, uint256 rad) external {
        dai[v]      = _add(dai[v],      rad);
        ghostDaiSum = _add(ghostDaiSum, rad); // BUG: dai grows, debt does NOT
    }

    function __check() public view {
        assert(ghostDaiSum == debt); // __INVARIANT__
    }
}
