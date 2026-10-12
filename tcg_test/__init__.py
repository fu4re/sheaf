"""tcg — trusted gate around vibe-coded Solidity (productization of ADR-0003).

The CLI wraps the validated `cycle/` substrate (F → gateway → K → measurement)
as a product surface that emits a safe outcome with a presentable assurance
package, and NEVER prints green `Verified(b, φ)` outside full ADR-conformance.

See docs/plans/adr-federated-parrot.md for the full design and the task series
docs/backlog/0006..0013 for the sliced increments.
"""
