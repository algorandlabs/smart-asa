"""
Smart ASA client
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

from base64 import b64decode
from typing import Optional, Union
from algosdk.abi import Contract
from algosdk.v2client.algod import AlgodClient
from algosdk.encoding import encode_address
from algosdk.future.transaction import OnComplete
from account import Account, AppAccount
from utils import get_global_state, get_method, get_params


def get_smart_asa_params(_algod_client: AlgodClient, smart_asa_id: int) -> dict:
    smart_asa = _algod_client.asset_info(smart_asa_id)["params"]
    smart_asa_app_id = int.from_bytes(b64decode(smart_asa["url-b64"]), "big")
    smart_asa_state = get_global_state(_algod_client, smart_asa_app_id)
    smart_asa_app = _algod_client.application_info(smart_asa_app_id)["params"]
    return {
        "smart_asa_id": smart_asa_id,
        "app_id": smart_asa_app_id,
        "creator_addr": smart_asa_app["creator"],
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


def smart_asa_create(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    creator: Account,
    total: int,
    decimals: int = 0,
    default_frozen: bool = False,
    unit_name: str = "",
    asset_name: str = "",
    url: str = "",
    metadata_hash: str = "",
    manager_addr: Optional[Union[str, Account]] = None,
    reserve_addr: Optional[Union[str, Account]] = None,
    freeze_addr: Optional[Union[str, Account]] = None,
    clawback_addr: Optional[Union[str, Account]] = None,
    save_abi_call: str = None,
) -> int:

    params = get_params(creator.algod_client)
    abi_call_fee = params.fee * 2

    return creator.abi_call(
        get_method(smart_asa_contract, "asset_create"),
        total,
        decimals,
        default_frozen,
        unit_name,
        asset_name,
        url,
        metadata_hash,
        manager_addr if manager_addr is not None else creator,
        reserve_addr if reserve_addr is not None else creator,
        freeze_addr if freeze_addr is not None else creator,
        clawback_addr if clawback_addr is not None else creator,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_optin(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    asset_id: int,
    caller: Account,
    save_abi_call: str = None,
) -> None:

    params = get_params(caller.algod_client)
    abi_call_fee = params.fee * 2

    caller.abi_call(
        get_method(smart_asa_contract, "asset_app_optin"),
        asset_id,
        on_complete=OnComplete.OptInOC,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_config(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    manager: Account,
    smart_asa_id: int,
    config_total: int = None,
    config_decimals: int = None,
    config_default_frozen: bool = None,
    config_unit_name: str = None,
    config_asset_name: str = None,
    config_url: str = None,
    config_metadata_hash: str = None,
    config_manager_addr: Optional[Account] = None,
    config_reserve_addr: Optional[Account] = None,
    config_freeze_addr: Optional[Account] = None,
    config_clawback_addr: Optional[Account] = None,
    save_abi_call: str = None,
) -> int:

    s_asa = get_smart_asa_params(manager.algod_client, smart_asa_id)

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
        smart_asa_id,
        s_asa["total"] if config_total is None else config_total,
        s_asa["decimals"] if config_decimals is None else config_decimals,
        s_asa["default_frozen"]
        if config_default_frozen is None
        else config_default_frozen,
        s_asa["unit_name"] if config_unit_name is None else config_unit_name,
        s_asa["name"] if config_asset_name is None else config_asset_name,
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
    return smart_asa_id


def smart_asa_transfer(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    xfer_asset: int,
    asset_amount: int,
    caller: Account,
    asset_receiver: Account,
    asset_sender: Optional[Account] = None,
    save_abi_call: str = None,
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
    asset_frozen: bool,
    save_abi_call: str = None,
) -> None:

    params = get_params(freezer.algod_client)
    abi_call_fee = params.fee * 2

    freezer.abi_call(
        get_method(smart_asa_contract, "asset_freeze"),
        freeze_asset,
        asset_frozen,
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
    account_frozen: bool,
    save_abi_call: str = None,
) -> None:

    params = get_params(freezer.algod_client)
    abi_call_fee = params.fee * 2

    freezer.abi_call(
        get_method(smart_asa_contract, "account_freeze"),
        freeze_asset,
        target_account,
        account_frozen,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )
