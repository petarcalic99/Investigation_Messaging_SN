// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Starknet messaging interface
interface IStarknetMessaging2 {
    function consumeMessageFromL2(uint256 fromAddress, uint256[] calldata payload) external returns (bytes32);

    function sendMessageToL2(
        uint256 toAddress,
        uint256 selector,
        uint256[] calldata payload
    ) external payable returns (bytes32, uint256);

    function l2ToL1Messages(bytes32 msgHash) external view returns (uint256);
}
