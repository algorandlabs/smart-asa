"""
Smart ASA client
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

from base64 import b64decode
from typing import Any, Optional, Union
from algosdk.abi import Contract
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import encode_address
from algosdk.future.transaction import OnComplete
from account import Account, AppAccount
from utils import get_global_state, get_method, get_params

from smart_asa_asc import (
    UNDERLYING_ASA_TOTAL,
    smart_asa_global_state,
    smart_asa_local_state,
)


def get_smart_asa_params(_algod_client: AlgodClient, smart_asa_id: int) -> dict:
    smart_asa = _algod_client.asset_info(smart_asa_id)["params"]
    smart_asa_app_id = int.from_bytes(b64decode(smart_asa["url-b64"]), "big")
    smart_asa_app_account = AppAccount.from_app_id(
        app_id=smart_asa_app_id,
        algod_client=_algod_client,
    )
    smart_asa_state = get_global_state(_algod_client, smart_asa_app_id)
    smart_asa_app = _algod_client.application_info(smart_asa_app_id)["params"]
    circulating_supply = UNDERLYING_ASA_TOTAL.value - smart_asa_app_account.asa_balance(
        smart_asa_id
    )
    return {
        "smart_asa_id": smart_asa_id,
        "app_id": smart_asa_app_id,
        "app_address": smart_asa_app_account.address,
        "creator_addr": smart_asa_app["creator"],
        "circulating_supply": circulating_supply,
        "unit_name": smart_asa_state["unit_name"].decode(),
        "name": smart_asa_state["name"].decode(),
        "url": smart_asa_state["url"].decode(),
        "metadata_hash": smart_asa_state["metadata_hash"].decode(),
        "total": int(smart_asa_state["total"]),
        "decimals": int(smart_asa_state["decimals"]),
        "frozen": bool(smart_asa_state["frozen"]),
        "default_frozen": bool(smart_asa_state["default_frozen"]),
        "manager_addr": encode_address(smart_asa_state["manager_addr"]),
        "reserve_addr": encode_address(smart_asa_state["reserve_addr"]),
        "freeze_addr": encode_address(smart_asa_state["freeze_addr"]),
        "clawback_addr": encode_address(smart_asa_state["clawback_addr"]),
    }


def smart_asa_app_create(
    teal_approval: str, teal_clear: str, creator: Account
) -> AppAccount:
    return creator.create_asc(
        approval_program=teal_approval,
        clear_program=teal_clear,
        global_schema=smart_asa_global_state,
        local_schema=smart_asa_local_state,
    )


def smart_asa_create(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    creator: Account,
    total: int,
    decimals: Optional[int] = None,
    default_frozen: Optional[bool] = None,
    unit_name: Optional[str] = None,
    name: Optional[str] = None,
    url: Optional[str] = None,
    metadata_hash: Optional[str] = None,
    manager_addr: Optional[Union[str, Account]] = None,
    reserve_addr: Optional[Union[str, Account]] = None,
    freeze_addr: Optional[Union[str, Account]] = None,
    clawback_addr: Optional[Union[str, Account]] = None,
    save_abi_call: Optional[str] = None,
) -> int:

    params = get_params(creator.algod_client)
    abi_call_fee = params.fee * 2

    return creator.abi_call(
        get_method(smart_asa_contract, "asset_create"),
        total,
        decimals if decimals is not None else 0,
        default_frozen if default_frozen is not None else False,
        unit_name if unit_name is not None else "",
        name if name is not None else "",
        url if url is not None else "",
        metadata_hash if metadata_hash is not None else "",
        manager_addr if manager_addr is not None else creator,
        reserve_addr if reserve_addr is not None else creator,
        freeze_addr if freeze_addr is not None else creator,
        clawback_addr if clawback_addr is not None else creator,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_app_optin(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    asset_id: int,
    caller: Account,
    save_abi_call: Optional[str] = None,
) -> None:

    params = get_params(caller.algod_client)
    abi_call_fee = params.fee

    caller.abi_call(
        get_method(smart_asa_contract, "asset_app_optin"),
        asset_id,
        on_complete=OnComplete.OptInOC,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_app_closeout(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    asset_id: int,
    closer: Account,
    save_abi_call: Optional[str] = None,
) -> None:

    params = get_params(closer.algod_client)
    abi_call_fee = params.fee

    closer.abi_call(
        get_method(smart_asa_contract, "asset_app_closeout"),
        asset_id,
        on_complete=OnComplete.CloseOutOC,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_config(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    manager: Account,
    asset_id: int,
    config_total: Optional[int] = None,
    config_decimals: Optional[int] = None,
    config_default_frozen: Optional[bool] = None,
    config_unit_name: Optional[str] = None,
    config_name: Optional[str] = None,
    config_url: Optional[str] = None,
    config_metadata_hash: Optional[str] = None,
    config_manager_addr: Optional[Union[str, Account]] = None,
    config_reserve_addr: Optional[Union[str, Account]] = None,
    config_freeze_addr: Optional[Union[str, Account]] = None,
    config_clawback_addr: Optional[Union[str, Account]] = None,
    save_abi_call: Optional[str] = None,
) -> int:

    s_asa = get_smart_asa_params(manager.algod_client, asset_id)

    if config_manager_addr is None:
        config_manager_addr = Account(address=s_asa["manager_addr"])
    if config_reserve_addr is None:
        config_reserve_addr = Account(address=s_asa["reserve_addr"])
    if config_freeze_addr is None:
        config_freeze_addr = Account(address=s_asa["freeze_addr"])
    if config_clawback_addr is None:
        config_clawback_addr = Account(address=s_asa["clawback_addr"])

    params = get_params(manager.algod_client)
    abi_call_fee = params.fee * 2

    manager.abi_call(
        get_method(smart_asa_contract, "asset_config"),
        asset_id,
        s_asa["total"] if config_total is None else config_total,
        s_asa["decimals"] if config_decimals is None else config_decimals,
        s_asa["default_frozen"]
        if config_default_frozen is None
        else config_default_frozen,
        s_asa["unit_name"] if config_unit_name is None else config_unit_name,
        s_asa["name"] if config_name is None else config_name,
        s_asa["url"] if config_url is None else config_url,
        s_asa["metadata_hash"]
        if config_metadata_hash is None
        else config_metadata_hash,
        config_manager_addr,
        config_reserve_addr,
        config_freeze_addr,
        config_clawback_addr,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )
    return asset_id


def smart_asa_transfer(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    xfer_asset: int,
    asset_amount: int,
    caller: Account,
    asset_receiver: Account,
    asset_sender: Optional[Union[str, Account]] = None,
    save_abi_call: Optional[str] = None,
) -> None:

    params = get_params(caller.algod_client)
    abi_call_fee = params.fee * 2

    caller.abi_call(
        get_method(smart_asa_contract, "asset_transfer"),
        xfer_asset,
        asset_amount,
        caller if asset_sender is None else asset_sender,
        asset_receiver,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_freeze(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    freezer: Account,
    freeze_asset: int,
    asset_frozen: Optional[bool] = None,
    save_abi_call: Optional[str] = None,
) -> None:

    params = get_params(freezer.algod_client)
    abi_call_fee = params.fee * 2

    freezer.abi_call(
        get_method(smart_asa_contract, "asset_freeze"),
        freeze_asset,
        False if asset_frozen is None else asset_frozen,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_account_freeze(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    freezer: Account,
    freeze_asset: int,
    target_account: Account,
    account_frozen: Optional[bool] = None,
    save_abi_call: Optional[str] = None,
) -> None:

    params = get_params(freezer.algod_client)
    abi_call_fee = params.fee * 2

    freezer.abi_call(
        get_method(smart_asa_contract, "account_freeze"),
        freeze_asset,
        target_account,
        False if account_frozen is None else account_frozen,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_destroy(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    manager: Account,
    destroy_asset: int,
    save_abi_call: Optional[str] = None,
) -> None:

    params = get_params(manager.algod_client)
    abi_call_fee = params.fee * 2

    manager.abi_call(
        get_method(smart_asa_contract, "asset_destroy"),
        destroy_asset,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_get(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    caller: Account,
    asset_id: int,
    getter: str,
    account: Optional[Union[str, Account]] = None,
    save_abi_call: Optional[str] = None,
) -> Any:
    args = [asset_id]
    if account is not None:
        args.append(account)
    return caller.abi_call(
        get_method(smart_asa_contract, getter),
        *args,
        app=smart_asa_app,
        save_abi_call=save_abi_call,
    )
