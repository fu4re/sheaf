# Provenance — MakerDAO DSS `Vat` (self-contained verification target)

Target for this cycle: the DSS `Vat` — the trusted CDP-accounting core. Chosen as a
**self-contained** complex contract (zero external calls; everyone calls IT) after the
ATokenVault spike showed Aave's economics are cross-contract (→ a future ADR).

| Field | Value |
|---|---|
| Repo | https://github.com/makerdao/dss |
| Commit | `fa4f6630afb0624d04a003e920b0d71a00331d98` |
| File | `src/vat.sol` (246 lines) → `legacy/Vat_0_6.sol` (byte-identical) |
| License | AGPL-3.0-or-later |
| Original pragma | `^0.6.12` |
| SUT | `src/Vat.sol` — `^0.8` port, equivalence-verified (see [port_notes.md](port_notes.md)) |

## Self-containment (confirmed)
No imports, no inheritance, no external calls — only internal mappings + pure
`assembly{or/and}`. Verified by grep: zero `.call`/interface/`I…(` references.

## Units (part of the complexity)
- `wad` = 1e18: `urns.ink`, `urns.art`, `ilks.Art`, `gem`
- `ray` = 1e27: `ilks.rate`, `ilks.spot`
- `rad` = 1e45: `dai`, `sin`, `debt`, `vice`, `Line`, `ilks.line`, `ilks.dust`

## Canonical conservation invariants (the expert ground truth)
Derived by tracing every state mutation (the documented Maker / K-framework invariants):

| id | law | exercises |
|---|---|---|
| `dai_conservation` | `Σ dai[u] == debt` | tracked-sum ghost |
| `sin_conservation` | `Σ sin[u] == vice` | tracked-sum ghost |
| `art_conservation` | `ilks[i].Art == Σ urns[i][u].art` | tracked-sum ghost |
| `debt_solvency` | `debt == vice + Σ_i (ilks[i].Art · ilks[i].rate)` | sum + ghost ray-mul (our Lean axioms) |
| `fee_monotonic` (fold) | accrual only increases `rate`/backed-debt consistently | temporal + ray-mul |

Target method: **`frob`** (lock collateral / draw debt — the deposit-analog).
Secondary: **`fold`** (rate accrual — the ray-mul arithmetic wall).
