// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// THE GAP (review point #1), made concrete. A BURNING fee-on-transfer token:
/// the skimmed fee is burned (totalSupply -= 1), NOT lost. So `Σ balanceOf` and
/// `totalSupply` drop in lockstep and CONSERVATION `ghostSum == totalSupply` STILL
/// HOLDS — the solver PROVES obligation-2-as-conservation here. Yet the recipient is
/// credited `amount - 1`, so the caller's mined guarantee (vault balance += >= assets)
/// is FALSE and the vault is insolvent. Conservation does NOT entail the delta clause
/// the caller actually relies on. This is why obligation 2 must discharge the DELTA
/// guarantee (see MiniERC20Delta.sol / BurnFeeERC20Delta.sol), not conservation.
contract BurnFeeERC20Conservation {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;
    uint256 public ghostSum; // shadow of Σ balanceOf

    function mint(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(totalSupply <= type(uint128).max, "supply cap");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[to] += amount;
        totalSupply   += amount;
        ghostSum      += amount;
    }

    function transfer(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(amount > 0, "zero");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[from] -= amount;
        balanceOf[to]   += amount - 1; // recipient under-credited
        totalSupply     -= 1;          // fee BURNED (not lost)
        ghostSum        -= 1;          // Σ drops by 1 — in lockstep with totalSupply
        // ghostSum == totalSupply STILL HOLDS ⇒ conservation proves, gap is real.
    }

    function __check() public view {
        assert(ghostSum == totalSupply); // __INVARIANT__ (gateway overwrites the expr)
    }
}
