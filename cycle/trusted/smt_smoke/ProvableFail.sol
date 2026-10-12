// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// T-01 smoke test (negative): a FALSE assertion the SMTChecker must REFUTE
/// by emitting a concrete counterexample.
///
/// Verdict expected from the solver core [5]: `counterexample + witness`
/// (witness: a == 1, or any odd value).
///
/// The property is deliberately on-theme for `deposit`: it claims that
/// integer division by 2 round-trips, which is FALSE precisely because of
/// rounding-down toward zero — the same rounding that governs assets->shares.
///
/// Run:
///   solc --model-checker-engine chc --model-checker-targets assert \
///        cycle/trusted/smt_smoke/ProvableFail.sol
contract ProvableFail {
    /// Claims `a / 2 * 2 == a`. Holds for even `a`, fails for odd `a`.
    /// The SMTChecker should surface the witness a = 1 (=> 0 != 1).
    function roundTripDivByTwo(uint256 a) external pure {
        assert((a / 2) * 2 == a); // REFUTED: counterexample a = 1
    }
}
