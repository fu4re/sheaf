// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// PRE-FIXED cross-contract assume-guarantee harness for VaultAsset (TRUSTED).
///
/// Obligation 1 (CALLER proof): prove the vault's solvency invariant I_A when each
/// external call to the ERC20 B is replaced by its SUMMARY = a CONSTRAINED HAVOC.
/// We do NOT compile B in and we do NOT call it: the call boundary is the wall
/// (Step-0: `untrusted` ext-calls synthesize the call as a reentrant callback →
/// the true invariant is refuted; `trusted` ext-calls inline+assume-no-reentrancy
/// → even a hostile token is PROVED, which is unsound). The A/G summary sits
/// between the two: it proves I_A relative to an EXPLICIT, named guarantee G_B
/// that is discharged separately against the real callee (obligation 2).
///
/// MECHANISM (identical to ProportionalVaultGhost's havoc'd `mintedShares`):
///   * the only cell of B's storage that I_A reads is balanceOf(address(vault));
///     we mirror it as `vaultBal`;
///   * each transfer becomes: havoc vaultBal (fresh input `vaultBal_post`, the
///     solver explores ALL post-balances) THEN require(__SUMMARY__) (assume G_B's
///     projection: vaultBal moved by exactly ±assets);
///   * I_A is proved RELATIVE to that frozen guarantee, never touching the call.
///
/// SOUNDNESS (the A/G frame, obligation 4): the summary writes ONLY `vaultBal`,
/// never `totalAssets` — i.e. it ASSUMES the transfer does not reenter A. That is
/// the curated, trusted part (ghost.md: too-strong axiom falsely proves). A
/// reentrant/fee token violates G_B and is caught by obligation 2's discharge, NOT
/// here. Too-weak summary merely fails to prove (safe); see VaultAssetAGBuggy.sol.
contract VaultAssetAG {
    uint256 public totalAssets; // A's internal accounting
    uint256 public vaultBal;    // mirror of asset.balanceOf(address(this)) — B's storage projection

    // deposit: external transferFrom(user, vault, assets) summarised.
    // `vaultBal_post` is the havoc'd result standing in for B's effect on
    // balanceOf(vault); the require pins it to the frozen guarantee G_B.
    function deposit(uint256 assets, uint256 vaultBal_post) public {
        require(assets    <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(vaultBal  <= type(uint128).max, "bal cap");

        require(vaultBal_post == vaultBal + assets); // __SUMMARY__ (gateway overwrites the expr)
        vaultBal = vaultBal_post; // commit the havoc'd post-state

        totalAssets += assets;

        assert(vaultBal >= totalAssets); // __INVARIANT__ (gateway overwrites the expr)
    }

    // withdraw: external transfer(user, assets) summarised.
    function withdraw(uint256 assets, uint256 vaultBal_post) public {
        require(assets <= totalAssets, "insufficient");

        totalAssets -= assets;

        require(vaultBal_post == vaultBal - assets); // __SUMMARY__ (gateway overwrites the expr)
        vaultBal = vaultBal_post;

        assert(vaultBal >= totalAssets); // __INVARIANT__ (gateway overwrites the expr)
    }
}
