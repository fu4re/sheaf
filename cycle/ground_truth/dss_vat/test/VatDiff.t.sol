// SPDX-License-Identifier: AGPL-3.0-or-later
pragma solidity ^0.8.0;

import {Test} from "forge-std/Test.sol";
import {Vat} from "../src/Vat.sol";

/// Differential equivalence test: the legacy 0.6.12 Vat and our 0.8 port get the
/// SAME fuzzed call sequence; after every call we assert (1) identical revert-ness
/// and (2) identical full observable state. Any divergence = the port broke mechanics.
interface IVat {
    function rely(address) external;
    function init(bytes32) external;
    function file(bytes32, uint256) external;
    function file(bytes32, bytes32, uint256) external;
    function slip(bytes32, address, int256) external;
    function frob(bytes32, address, address, address, int256, int256) external;
    function fold(bytes32, address, int256) external;
    function grab(bytes32, address, address, address, int256, int256) external;
    function move(address, address, uint256) external;
    function heal(uint256) external;
    function suck(address, address, uint256) external;
    function ilks(bytes32) external view returns (uint256, uint256, uint256, uint256, uint256);
    function urns(bytes32, address) external view returns (uint256, uint256);
    function gem(bytes32, address) external view returns (uint256);
    function dai(address) external view returns (uint256);
    function sin(address) external view returns (uint256);
    function debt() external view returns (uint256);
    function vice() external view returns (uint256);
    function Line() external view returns (uint256);
    function live() external view returns (uint256);
}

contract VatDiffTest is Test {
    IVat a; // legacy 0.6.12
    IVat b; // 0.8 port
    bytes32[2] ilks_;
    address[3] usrs_;

    function setUp() public {
        b = IVat(address(new Vat()));
        // legacy 0.6.12 deployed from bytecode precompiled by its own solc 0.6.12
        // (forge's 0.6.12 sub-compile spuriously stack-too-deeps; the contract itself
        // compiles fine — see legacy/Vat_0_6.sol + test/vat_0_6.bin).
        bytes memory code = vm.parseBytes(vm.readFile("test/vat_0_6.bin"));
        address legacy;
        assembly { legacy := create(0, add(code, 0x20), mload(code)) }
        require(legacy != address(0), "legacy deploy failed");
        a = IVat(legacy);
        ilks_ = [bytes32("GOLD"), bytes32("SILVER")];
        usrs_ = [address(this), address(0xA11CE), address(0xB0B)];
        // identical permissive setup on both so frob/fold reach success paths often
        for (uint256 i = 0; i < 2; i++) {
            bytes32 ilk = ilks_[i];
            a.init(ilk);                       b.init(ilk);
            a.file(ilk, "line", 1e45);         b.file(ilk, "line", 1e45);
            a.file(ilk, "spot", 1e27);         b.file(ilk, "spot", 1e27);
            a.file(ilk, "dust", 0);            b.file(ilk, "dust", 0);
        }
        a.file("Line", 1e60);                  b.file("Line", 1e60);
        _assertStateEqual(); // start equal
    }

    function _ilk(uint256 s) internal view returns (bytes32) { return ilks_[s % 2]; }
    function _usr(uint256 s) internal view returns (address) { return usrs_[s % 3]; }
    function _bnd(int256 x, int256 mag) internal pure returns (int256) { return bound(x, -mag, mag); }

    function _diff(bytes memory cd) internal {
        (bool oka, ) = address(a).call(cd);
        (bool okb, ) = address(b).call(cd);
        assertEq(oka, okb, "REVERT PARITY BROKEN");
    }

    function _encode(uint256 seed, int256 d1, int256 d2) internal view returns (bytes memory) {
        uint256 op = seed % 9;
        bytes32 ilk = _ilk(seed >> 8);
        address u = address(this);          // urn owner / collateral src = us (consent passes)
        address w = _usr(seed >> 16);       // dai / debt destination
        if (op == 0) return abi.encodeWithSignature("init(bytes32)", ilk);
        if (op == 1) return abi.encodeWithSignature("file(bytes32,uint256)", bytes32("Line"), uint256(bound(d1, 0, 1e60)));
        if (op == 2) {
            bytes32 what = bytes32("spot");
            uint256 wsel = (seed >> 24) % 3;
            if (wsel == 1) what = bytes32("line");
            else if (wsel == 2) what = bytes32("dust");
            return abi.encodeWithSignature("file(bytes32,bytes32,uint256)", ilk, what, uint256(bound(d1, 0, 1e45)));
        }
        if (op == 3) return abi.encodeWithSignature("slip(bytes32,address,int256)", ilk, u, _bnd(d1, 1e24));
        if (op == 4) return abi.encodeWithSignature("frob(bytes32,address,address,address,int256,int256)", ilk, u, u, w, _bnd(d1, 1e24), _bnd(d2, 1e24));
        if (op == 5) return abi.encodeWithSignature("fold(bytes32,address,int256)", ilk, w, _bnd(d1, 1e26));
        if (op == 6) return abi.encodeWithSignature("move(address,address,uint256)", u, w, uint256(bound(d1, 0, 1e50)));
        if (op == 7) return abi.encodeWithSignature("grab(bytes32,address,address,address,int256,int256)", ilk, u, u, w, _bnd(d1, 1e24), _bnd(d2, 1e24));
        return abi.encodeWithSignature("suck(address,address,uint256)", w, u, uint256(bound(d1, 0, 1e45)));
    }

    function testFuzz_equivalence(uint256[16] calldata seeds, int256[16] calldata d1, int256[16] calldata d2) public {
        for (uint256 k = 0; k < 16; k++) {
            _diff(_encode(seeds[k], d1[k], d2[k]));
            _assertStateEqual();
        }
    }

    function _assertStateEqual() internal {
        assertEq(a.debt(), b.debt(), "debt");
        assertEq(a.vice(), b.vice(), "vice");
        assertEq(a.Line(), b.Line(), "Line");
        assertEq(a.live(), b.live(), "live");
        for (uint256 i = 0; i < 2; i++) {
            _eqIlk(ilks_[i]);
            for (uint256 j = 0; j < 3; j++) _eqUrn(ilks_[i], usrs_[j]);
        }
        for (uint256 j = 0; j < 3; j++) {
            assertEq(a.dai(usrs_[j]), b.dai(usrs_[j]), "dai");
            assertEq(a.sin(usrs_[j]), b.sin(usrs_[j]), "sin");
        }
    }

    function _eqIlk(bytes32 ilk) internal {
        (uint256 A1, uint256 r1, uint256 s1, uint256 l1, uint256 u1) = a.ilks(ilk);
        (uint256 A2, uint256 r2, uint256 s2, uint256 l2, uint256 u2) = b.ilks(ilk);
        assertEq(A1, A2, "Art"); assertEq(r1, r2, "rate"); assertEq(s1, s2, "spot");
        assertEq(l1, l2, "line"); assertEq(u1, u2, "dust");
    }

    function _eqUrn(bytes32 ilk, address usr) internal {
        (uint256 ink1, uint256 art1) = a.urns(ilk, usr);
        (uint256 ink2, uint256 art2) = b.urns(ilk, usr);
        assertEq(ink1, ink2, "ink"); assertEq(art1, art2, "art");
        assertEq(a.gem(ilk, usr), b.gem(ilk, usr), "gem");
    }
}
