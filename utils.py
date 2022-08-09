import base64
from collections import namedtuple
from typing import Union
from algosdk import constants
from algosdk.future import transaction
from algosdk.v2client import algod


def decode_state(state) -> dict[str, Union[int, bytes]]:
    return {
        # We are assuming that global space `key` are printable.
        # If that's not necessarily true, we can change that.
        base64.b64decode(s["key"]).decode(): base64.b64decode(s["value"]["bytes"])
        if s["value"]["type"] == 1
        else int(s["value"]["uint"])
        for s in state
    }


def get_global_state(
    algod_client: algod.AlgodClient, asc_idx: int
) -> dict[str, Union[bytes, int]]:
    global_state = algod_client.application_info(asc_idx)["params"]["global-state"]
    global_state = decode_state(global_state)
    return global_state


def get_local_state(
    algod_client: algod.AlgodClient, account_address: str, asc_idx: int
) -> dict[str, Union[bytes, int]]:
    local_states = algod_client.account_info(account_address)["apps-local-state"]
    local_state = [s for s in local_states if s["id"] == asc_idx][0].get(
        "key-value", {}
    )
    local_state = decode_state(local_state)
    return local_state


def get_params(
    algod_client: algod.AlgodClient, fee: int = None
) -> transaction.SuggestedParams:
    params = algod_client.suggested_params()
    params.flat_fee = True
    params.fee = fee or constants.MIN_TXN_FEE
    return params


def get_last_round(algod_client: algod.AlgodClient):
    return algod_client.status()["last-round"]


def get_last_timestamp(algod_client: algod.AlgodClient):
    return algod_client.block_info(get_last_round(algod_client))["block"]["ts"]


def assemble_program(algod_client: algod.AlgodClient, source_code: str) -> bytes:
    compile_response = algod_client.compile(source_code)
    return base64.b64decode(compile_response["result"])


# NOTE: getter_params represents a tuple of three tuples. This utility
# will be removed once PyTeal integrates the ABI type NamedTuple
SmartASAConfig = namedtuple(
    "SmartASAConfig",
    [
        "total",
        "decimals",
        "default_frozen",
        "unit_name",
        "name",
        "url",
        "metadata_hash",
        "manager_addr",
        "reserve_addr",
        "freeze_addr",
        "clawback_addr",
    ],
)


def normalize_getter_params(getter_params: list) -> SmartASAConfig:

    return SmartASAConfig(
        getter_params[0][0],
        getter_params[0][1],
        getter_params[0][2],
        getter_params[0][3],
        getter_params[0][4],
        getter_params[1][0],
        getter_params[1][1],
        getter_params[1][2],
        getter_params[1][3],
        getter_params[1][4],
        getter_params[2][0],
    )
