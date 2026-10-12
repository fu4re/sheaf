// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract D {
    mapping(uint256 => uint256) public m;
    // Unsupported precondition construct: mapping access m[0].
    /// @custom:kontrol-precondition m[0] > 10,
    function h(uint256 x) public view returns (uint256) {
        return x + m[0];
    }
}
