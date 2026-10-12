// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Non-vacuity sibling of MiniERC20Conservation.sol: a callee whose `mintUnbacked`
/// credits a balance WITHOUT raising totalSupply (supply-inflation bug). The
/// conservation guarantee G_B is then FALSE, so obligation 2 must REFUTE it — the
/// solver returns a counterexample, exactly as it should for a token that does not
/// satisfy its advertised guarantee. Confirms the discharge harness is not vacuous
/// (a `proved` here would be meaningless) and that obligation 2 catches a bad callee.
contract MiniERC20ConservationBuggy {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
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

    function mintUnbacked(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[to] += amount; // BUG: balance grows...
        ghostSum      += amount; // ...Σ grows...
        // ...but totalSupply is NOT raised ⇒ ghostSum > totalSupply ⇒ G_B violated.
    }

    function __check() public view {
        assert(ghostSum == totalSupply); // __INVARIANT__ (gateway overwrites the expr)
    }
}
