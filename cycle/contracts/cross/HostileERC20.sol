// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Adversarial callee B' — ERC777-style reentrancy. `transferFrom` invokes a hook
/// on the recipient (the vault) MID-TRANSFER, before the credit settles. A hook
/// that reenters Vault.deposit mutates A's totalAssets while B's balance is in an
/// intermediate state — exactly the cross-call interleaving the A/G summary FORBIDS.
///
/// STATUS — CONCEPTUAL EXHIBIT (honest scoping): this is a *domain illustration* of
/// the frame (no-reentrancy) assumption, NOT a runnable attack harness — VaultAsset
/// implements no `tokensReceived` hook and this contract is not wired into triage.
/// The RUNNABLE reentrancy evidence is the Step-0 probe B3 (scratch `p_b3_selfhavoc`),
/// where SMTChecker *itself* synthesized the external call as a reentrant `setX` call
/// and REFUTED the no-self-mutation assert — proving reentrancy is modeled by default.
/// A full runnable reentrancy-attack harness (vault hook + refuted solvency) is a
/// named next step. The frame remains the residual TRUSTED assumption of the summary.
///
/// Why it belongs to the frame, not obligation 2:
///   * obligation 2 (B ⊨ G_B as a *state* property of B) does NOT see this — B's
///     own conservation can still hold; the violation is the FRAME (B calling back
///     into A), which is the residual trusted assumption of the summary;
///   * SMTChecker's `untrusted` ext-calls model this reentrancy by default (Step-0
///     B3: "untrusted external call, synthesized as ... reentrant call"), but then
///     it refutes EVERYTHING (the wall); its `trusted`+interface mode is VACUOUS
///     (Step-0: proves assert(false)). The A/G summary is the only mode that proves
///     I_A while naming the no-reentrancy frame as an explicit assumption.
interface IDepositHook {
    function tokensReceived(address from, uint256 amount) external;
}

contract HostileERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(allowance[from][msg.sender] >= amount, "allowance");
        require(balanceOf[from] >= amount, "insufficient");
        allowance[from][msg.sender] -= amount;
        balanceOf[from]             -= amount;
        // HOOK BEFORE CREDIT — reentrancy window: `to` (the vault) can call back
        // into deposit() while this transfer is only half-applied.
        IDepositHook(to).tokensReceived(from, amount);
        balanceOf[to] += amount;
        return true;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient");
        balanceOf[msg.sender] -= amount;
        IDepositHook(to).tokensReceived(msg.sender, amount);
        balanceOf[to] += amount;
        return true;
    }
}
