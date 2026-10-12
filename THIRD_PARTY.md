# Third-party material

The MIT licence in `LICENSE` covers the code and documents written for this
project. The items below are third-party and keep their own terms.

| Path | Origin | Licence | Status in this repo |
|---|---|---|---|
| `cycle/ground_truth/dss_vat/legacy/Vat_0_6.sol` | [makerdao/dss](https://github.com/makerdao/dss) `fa4f6630`, `src/vat.sol`, byte-identical | AGPL-3.0-or-later | committed |
| `cycle/ground_truth/dss_vat/src/Vat.sol`, `test/VatDiff.t.sol` | our 0.8 port of the above and its differential test (derived work) | AGPL-3.0-or-later | committed |
| `cycle/trusted/harness/Vat*.sol` | proof harnesses that inherit the ported `Vat` (derived work) | AGPL-3.0-or-later | committed (the generated copies under `cycle/measurement/artifacts/build/` are not) |
| `cycle/ground_truth/dss_vat/lib/forge-std` | [foundry-rs/forge-std](https://github.com/foundry-rs/forge-std) `257559546b763ec5fa7371fb77fef9102db86446` | MIT / Apache-2.0 | not committed; `forge install foundry-rs/forge-std@257559546b763ec5fa7371fb77fef9102db86446` |
| `cycle/ground_truth/aave_vault/src/*.sol`, `certora_specs/*.spec` | [aave/Aave-Vault](https://github.com/aave/Aave-Vault) `5ab52d20b07f35a8f34e6702f2fea6797a5787eb` | All Rights Reserved © Aave Labs | not committed; run `cycle/ground_truth/aave_vault/fetch.sh` (research reference only, see `PROVENANCE.md`) |
| `cycle/trusted/proofs/aave_arith/.lake/` | [leanprover-community/mathlib4](https://github.com/leanprover-community/mathlib4) v4.31.0 | Apache-2.0 | not committed; `lake exe cache get` |
| `kprove-test/repro/**` K specs | written against KEVM 1.0.678 ([runtimeverification/evm-semantics](https://github.com/runtimeverification/evm-semantics)) | BSD-3-Clause (KEVM) | kompiled outputs not committed |

Reproduction artefacts (JSON, logs, agent transcripts) under `cycle/measurement/artifacts/`,
`cycle/naive_loop/runs/` and `kprove-test/{logs,repro}` were produced on the
author's machine and contain its absolute paths. They are evidence, not inputs;
every command in `README.md` regenerates them.
