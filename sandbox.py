import functools
import time
from algosdk.kmd import KMDClient
from algosdk.v2client import algod
from algosdk.wallet import Wallet

from account import Account
from utils import get_last_round, get_last_timestamp


class Sandbox:
    ALGOD_ADDRESS = "http://localhost:4001"
    ALGOD_TOKEN = "a" * 64
    KMD_ADDRESS = "http://localhost:4002"
    KMD_TOKEN = "a" * 64

    algod_client = algod.AlgodClient(
        algod_token=ALGOD_TOKEN, algod_address=ALGOD_ADDRESS
    )
    kmd_client = KMDClient(kmd_token=KMD_TOKEN, kmd_address=KMD_ADDRESS)

    @classmethod
    @functools.lru_cache()
    def faucet(cls) -> Account:
        default_wallet_name = cls.kmd_client.list_wallets()[0]["name"]
        # Sandbox's wallet has no password
        wallet = Wallet(default_wallet_name, "", cls.kmd_client)

        for account in wallet.list_keys():
            info = cls.algod_client.account_info(account)
            if (
                info
                and info.get("status") == "Online"
                # and info.get("created-at-round", 0) == 0  # Needs the indexer.
            ):
                return Account(
                    account, wallet.export_key(account), algod_client=cls.algod_client
                )

        raise KeyError("Could not find sandbox faucet")

    @classmethod
    def from_public_key(cls, account: str):
        default_wallet_name = cls.kmd_client.list_wallets()[0]["name"]
        # Sandbox's wallet has no password
        wallet = Wallet(default_wallet_name, "", cls.kmd_client)
        return Account(
            account, wallet.export_key(account), algod_client=cls.algod_client
        )

    @classmethod
    def create(cls, funds_amount: int) -> Account:
        new_account = Account.create(algod_client=cls.algod_client)
        cls.faucet().pay(new_account, funds_amount)
        return new_account


def generate_blocks(account: Account, num_blocks: int):
    for _ in range(num_blocks):
        account.pay(account, 0)


def wait_until_round(algod_client: algod.AlgodClient, round: int, verbose=True):
    """Returns right after round `round` happened"""
    if verbose:
        print(f" --- ⏲️  Waiting until round: {round}.")
    if (delta := round - get_last_round(algod_client)) > 0:
        generate_blocks(Sandbox.faucet(), delta)


def wait_until_ts(algod_client: algod.AlgodClient, timestamp: int, verbose=True):
    if verbose:
        print(
            f" --- ⏲️  Waiting until ts: {timestamp}.",
            f"(expected wait: {timestamp - get_last_timestamp(algod_client)}s)",
        )
    old_ts = 0
    while (curr_ts := get_last_timestamp(algod_client)) < timestamp:
        generate_blocks(Sandbox.faucet(), 1)
        # If delta >= 25 we are still catching up, no need to sleep
        if curr_ts - old_ts < 25:
            time.sleep(1)
        old_ts = curr_ts
