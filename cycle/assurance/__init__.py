"""sheaf assurance package — reusable session-artifact format (Task 0003 / T2).

Format-only core: knows the shape of an assurance package and nothing about how it
was produced. See FORMAT.md for the normative spec.

  schema.py            structural shape of the three normative files
  verify_package.py    cross-file invariants (closure, acyclicity, evidence, honesty)
  adapters/            the only engine-aware seam (orchestrator/solver/LLM -> format)
"""
from .schema import (  # noqa: F401
    AssuranceGraph,
    Assumption,
    Claim,
    Edge,
    Evidence,
    HarnessFaithfulness,
    Ledger,
    LeanTheorem,
    SchemaError,
)
