import base64
from typing import Union
from algosdk import constants, abi
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

    if 'is_frozen' in local_state:
        local_state['frozen'] = local_state['is_frozen']
        del local_state['is_frozen']
    if 'current_asa_id' in local_state:
        local_state['smart_asa_id'] = local_state['current_asa_id']
        del local_state['current_asa_id']
    return local_state


def get_params(
    algod_client: algod.AlgodClient, fee: int = None
) -> transaction.SuggestedParams:
    params = algod_client.suggested_params()
    params.flat_fee = True
    params.fee = fee or constants.MIN_TXN_FEE
    return params


def get_method(contract: abi.Contract, name: str) -> abi.Method:
    for m in contract.methods:
        if m.name == name:
            return m
    raise Exception("No method with the name {}".format(name))


def get_last_round(algod_client: algod.AlgodClient):
    return algod_client.status()["last-round"]


def get_last_timestamp(algod_client: algod.AlgodClient):
    return algod_client.block_info(get_last_round(algod_client))["block"]["ts"]


def assembly_program(algod_client: algod.AlgodClient, source_code: str) -> bytes:
    compile_response = algod_client.compile(source_code)
    return base64.b64decode(compile_response["result"])
