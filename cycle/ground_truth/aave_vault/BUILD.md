# Building real ATokenVault for SMTChecker (Task 0002, variant-A spike)

Result of the spike: **the real `ATokenVault` IS ingestible by our contour** — it
compiles under our pinned native solc 0.8.35 and SMTChecker (CHC + z3) engages on
it. But raw analysis of the full 656-line contract with all inherited machinery
hits a **complexity wall**, so clean economic-invariant triage needs a FOCUSED
harness (as Certora does: `certora/harness/` munged + DummyERC20 + SymbolicLendingPool).

## Materialize the buildable project (deps are git submodules, not vendored)

```bash
git clone https://github.com/aave/Aave-Vault.git /tmp/aave-vault   # @ 5ab52d2
cd /tmp/aave-vault
git submodule update --init --recursive \
  lib/aave-v3-core lib/aave-v3-periphery \
  lib/openzeppelin-contracts-upgradeable lib/openzeppelin-contracts
# NOTE: do NOT use --depth 1 on a re-init — submodules pin exact commits (old OZ-v4
# names like ERC4626Upgradeable); shallow can grab the wrong tip.
```

## Compile-check (foundry-style relative remappings + base-path)

```bash
cd /tmp/aave-vault && solc \
  @aave-v3-core=lib/aave-v3-core/contracts \
  @aave-v3-periphery/=lib/aave-v3-periphery/contracts/ \
  @openzeppelin-upgradeable/=lib/openzeppelin-contracts-upgradeable/contracts/ \
  @openzeppelin/=lib/openzeppelin-contracts/contracts/ \
  solmate/=lib/solmate/src/ \
  --base-path . --include-path lib --allow-paths . \
  src/ATokenVault.sol
# => compiles (only dependency deprecation/shadow warnings)
```

## SMTChecker probe (CHC, restricted to ATokenVault)

Add: `--model-checker-engine chc --model-checker-targets overflow
--model-checker-solvers z3 --model-checker-contracts "src/ATokenVault.sol:ATokenVault"
--model-checker-timeout 3000`

**Observed:** `CHC: 7 verification condition(s) could not be proved` (overflow).
The unproved VCs are in INHERITED machinery — `ECDSAUpgradeable`, `IncentivizedERC20`
(ERC20 base), `StringsUpgradeable`/`AddressUpgradeable` — i.e. the complexity wall of
the whole real contract, not the deposit `rayMul`/`mulDiv` (those live in libraries and
get abstracted under the restriction).

## Implication for the measurement

For real economic-invariant triage we need a **focused Aave harness** that strips the
signature/ERC20/string machinery and abstracts `rayMul`/`rayDiv`/`mulDiv` via the
ghost (whose axioms are now Lean-proven, `cycle/trusted/proofs/`). That harness is the
Phase-2-remainder deliverable; it mirrors Certora's munged harness.
