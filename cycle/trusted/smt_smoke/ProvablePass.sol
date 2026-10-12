// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// T-01 smoke test (positive): a TRUE assertion the SMTChecker must PROVE.
///
/// Verdict expected from the solver core [5]: `proved`
/// (no counterexample emitted for the `assert` target).
///
/// Run:
///   solc --model-checker-engine chc --model-checker-targets assert \
///        cycle/trusted/smt_smoke/ProvablePass.sol
contract ProvablePass {
    /// Adding 1 strictly increases an unsigned value, given no overflow.
    /// The `require` rules out the only counterexample (x == max), so the
    /// post-condition is unconditionally true on the reachable state space.
    function monotonicAdd(uint256 x) external pure {
        require(x < type(uint256).max);
        uint256 y = x + 1;
        assert(y > x); // PROVED: holds for every reachable x
    }
}
