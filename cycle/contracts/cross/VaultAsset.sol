// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Tier-3 cross-contract SUT — a vault holding a REAL external ERC20 (the callee B).
///
/// Unlike MiniVault/ProportionalVault, where `assets` is a fiction (a bare
/// counter), here `totalAssets` is internal accounting that MUST stay coupled to
/// the token's OWN storage, in another contract. The honest economic law is
/// cross-contract SOLVENCY:
///     asset.balanceOf(address(this)) >= totalAssets
/// (the vault holds at least what it accounts; a direct donation only strengthens
/// it, so `>=`, not `==`). Proving it requires reasoning THROUGH the external
/// call — exactly what SMTChecker havocs by default (Step-0 wall: `untrusted`
/// ext-calls synthesize the call as a reentrant callback → assertion violation).
///
/// Arithmetic is 1:1 (linear) on purpose: the ONLY wall under study here is the
/// external-CALL boundary, not nonlinear mulDiv (that wall is mapped separately
/// in measurement/wall_map.md). One wall per exhibit.
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address who) external view returns (uint256);
}

contract VaultAsset {
    IERC20  public asset;
    uint256 public totalAssets;

    constructor(IERC20 _asset) {
        asset = _asset;
    }

    function deposit(uint256 assets) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        asset.transferFrom(msg.sender, address(this), assets); // EXTERNAL CALL to B
        totalAssets += assets;
    }

    function withdraw(uint256 assets) public {
        require(assets <= totalAssets, "insufficient");
        totalAssets -= assets;
        asset.transfer(msg.sender, assets); // EXTERNAL CALL to B
    }
}
