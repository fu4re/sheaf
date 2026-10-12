// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract B {
    /// @custom:kontrol-precondition x > 10,
    function f(uint256 x) public pure returns (uint256) {
        return x;
    }
}
