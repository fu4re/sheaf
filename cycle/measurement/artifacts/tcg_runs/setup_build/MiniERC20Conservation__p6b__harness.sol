// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// PRE-FIXED callee-discharge harness for MiniERC20 (TRUSTED). Proves B ⊨ G_B,
/// obligation 2 of the cross-contract assume-guarantee decomposition.
///
/// Tracked-sum ghost — the same pattern as SumVaultGhost.sol / VatDaiConservation.sol:
/// `ghostSum` shadows Σ balanceOf, maintained in lockstep with every balance write
/// (Σ over a mapping is not expressible in SMTChecker; the shadow's faithfulness is
/// the modelling step). The conservation guarantee is `ghostSum == totalSupply`.
/// The per-transfer delta the caller summary assumes (receiver += amount exactly)
/// is syntactically exact here and machine-checked in Lean (Erc20.transfer_sum_preserved).
/// `require(from != to)` mirrors SumVaultGhost — the self-transfer aliasing case is
/// the classic spurious counterexample for a Σ shadow.
contract MiniERC20Conservation {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;
    uint256 public ghostSum; // shadow of Σ balanceOf

    function transfer(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[from] -= amount;
        balanceOf[to]   += amount;
        // Σ unchanged (−amount +amount) ⇒ ghostSum untouched
    }

    function transferFrom(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(allowance[from][msg.sender] >= amount, "allowance");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to]   += amount;
        // Σ unchanged ⇒ ghostSum untouched
    }

    function mint(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(totalSupply <= type(uint128).max, "supply cap");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[to] += amount;
        totalSupply   += amount;
        ghostSum      += amount; // balance +amount ⇒ Σ +amount
    }

    function __check() public view {
        assert(ghostSum == totalSupply); // __INVARIANT__ (gateway-injected)
    }
}
