// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Escrow {
    address public customer; // заказчик (вносит оплату)
    address public provider; // исполнитель (получает оплату)
    uint256 public amount;   // сумма сделки (внесённый ETH)
    uint256 public deadline; // дедлайн (unix-время)

    bool public created;  // сделка создана и оплачена
    bool public started;  // исполнитель отметил, что начал работу
    bool public released; // средства уже выплачены или возвращены (сделка закрыта)




    uint256 public paidOut;


    function createDeal(address _provider, uint256 _deadline) external payable {
        require(!created, "deal exists");
        require(_provider != address(0), "provider=0");
        require(_provider != msg.sender, "provider==customer");
        require(msg.value > 0, "amount=0");
        require(_deadline > block.timestamp, "deadline in past");

        customer = msg.sender;
        provider = _provider;
        amount = msg.value;
        deadline = _deadline;
        created = true;
    }




    function startWork() external {
        require(created, "no deal");
        require(msg.sender == provider, "only provider");
        require(!released, "closed");
        started = true;
    }


    function approveWork() external {
        require(created, "no deal");
        require(msg.sender == customer, "only customer");
        require(!released, "closed");

        released = true;
        paidOut += amount;

        (bool ok, ) = provider.call{value: amount}("");
        require(ok, "transfer failed");
    }




    function refund() external {
        require(created, "no deal");
        require(msg.sender == customer, "only customer");
        require(!released, "closed");
        require(!started || block.timestamp > deadline, "work in progress");

        released = true;
        paidOut += amount;

        (bool ok, ) = customer.call{value: amount}("");
        require(ok, "transfer failed");
    }
}

contract __ReachHarness is Escrow {
    function __check_invariant() public view {
        assert(paidOut <= amount); // __INVARIANT__ (reachability probe injects false)
    }
}
