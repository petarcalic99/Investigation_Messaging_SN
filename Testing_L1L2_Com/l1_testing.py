import subprocess
import time

def open_terminal_and_run_command(command, terminal_label):
    """
    Opens a gnome-terminal and run the specified command
    """
    print(f"Starting {terminal_label}: {command}")
    print("\n")
    process = subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{command}; exec bash'])
    return process

############### SETUP ###############

# 1 Open anvil (local l1 node) in terminal_l1
launch_anvil = "anvil --fork-url https://eth-mainnet.g.alchemy.com/v2/ahUN0V5iw3yB0MlC9psJRUWFPSgIRFrx"
terminal_l1 = subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{launch_anvil}; exec bash'])
print("Anvil started in terminal_l1.")
# Wait a bit for anvil to initialize L1
time.sleep(3)

# 2 Open a new terminal and deploy the messaging contract
# We call this terminal_anvil as it will serve for the interaction with Ethereum
anvil_script_commands = [
    "cd solidity",
    "forge install",
    "cp anvil.env .env",
    "source .env",
    "forge script script/LocalTesting.s.sol:LocalSetup --broadcast --rpc-url ${ETH_RPC_URL}"
]
terminal_anvil_command = " && ".join(anvil_script_commands)
terminal_anvil = open_terminal_and_run_command(terminal_anvil_command, "terminal_anvil")
terminal_anvil.wait()

# 3 In a new terminal_l2, set up the L2 environment, katana is the L2 local node
l2_commands = [
    "starkliup",
    "dojoup -v 1.0.0-alpha.0",
    "katana --messaging anvil.messaging.json"
]
terminal_l2_command = " && ".join(l2_commands)
open_terminal_and_run_command(terminal_l2_command, "terminal_l2")
# Wait for the L2 setup to start
time.sleep(26)

# 4 In a new terminal deploy and set up the L2 contract
# We call this terminal_katana, as it will serve for the interaction with Starknet
katana_commands = [
    "cd cairo",
    "source katana.env",
    "scarb build",
    "starkli declare ./target/dev/messaging_tuto_contract_msg.contract_class.json --keystore-password ''",
    "starkli deploy 0x06ed2a2322c9d5786dddca690c8f809ada0046e1b15342755dc939706e9fb8c8 --salt 0x1234 --keystore-password ''"
]
terminal_katana_command = " && ".join(katana_commands)
terminal_katana = open_terminal_and_run_command(terminal_katana_command, "terminal_katana")
time.sleep(5)


########## L2 -> L1 MESSAGING ##########

send_to_l1_commands = [
    "cd cairo",
    "source katana.env",
    "starkli invoke 0x054ed08174d23bb79f871e5149f843b34d1692e459fb84d562ffa42a8fc9ab92 send_message_value 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512 1 --keystore-password ''"
]
terminal_send_to_l1_commands = " && ".join(send_to_l1_commands)
terminal_send_to_l1 = open_terminal_and_run_command(terminal_send_to_l1_commands, "terminal_send_to_l1_commands")
time.sleep(4)

consume_message_commands = [
    "cd solidity",
    "source .env",
    "forge script script/ConsumeMessage.s.sol:Value --broadcast -vvvv --rpc-url ${ETH_RPC_URL}"
]
terminal_consume_message_commands = " && ".join(consume_message_commands)
terminal_consume_message = open_terminal_and_run_command(terminal_consume_message_commands, "terminal_consume_message_commands")
time.sleep(4)
