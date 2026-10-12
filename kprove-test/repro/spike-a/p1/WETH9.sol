// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

// SPIKE-A / П-1 object: minimal WETH9 fragment.
// deposit() payable + withdraw(uint) with checks-effects-interactions.
// withdraw_F class (require>= ; debit ; xfer) — matches the t3-q1 model instance
// used as the П-2 (i) baseline, so "same property class on two carriers" is honest.
contract WETH9 {
    mapping(address => uint256) public balanceOf;

    function deposit() external payable {
        balanceOf[msg.sender] += msg.value;
    }

    function withdraw(uint256 wad) external {
        require(balanceOf[msg.sender] >= wad);   // Pre
        balanceOf[msg.sender] -= wad;            // effect: debit by exactly wad
        (bool ok, ) = payable(msg.sender).call{value: wad}("");  // interaction
        require(ok);
    }
}
