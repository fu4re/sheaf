// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// DELIBERATELY-VACUOUS FIXTURE (T1 vacuity-gate self-test) — the realistic DEAD-PATH
/// trap, reproducing the historical "totalSupply-always-0 → revert → unreachable"
/// vacuity bug. There is NO mint, so `totalSupply` is forever 0; the only mutator does
/// `totalSupply -= 1`, which underflows on the all-zero initial state and ALWAYS reverts
/// (0.8.x checked arithmetic). Every statement after it — including the invariant assert
/// — is therefore UNREACHABLE, so the assert proves VACUOUSLY. Probe R MUST flag it:
/// substituting the invariant with `false` still PROVES.
///
/// Contrast with the require(false) fixture (VaultAssetAGDead): there the dead-ness is an
/// explicit guard; here it is an emergent arithmetic-revert — the shape that actually bit.
contract MiniERC20NoMintConservation {
    uint256 public totalSupply; // never minted ⇒ always 0
    uint256 public ghostSum;

    function burn() public {
        totalSupply -= 1; // underflow on 0 ⇒ ALWAYS REVERTS ⇒ everything below is dead code
        assert(ghostSum == totalSupply); // __INVARIANT__ (unreachable ⇒ vacuous)
    }
}
