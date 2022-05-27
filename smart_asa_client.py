"""
Smart ASA client
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

from typing import Optional, Union
from algosdk import algod
from algosdk.abi import Contract
from algosdk.encoding import encode_address
from account import Account, AppAccount
from smart_asa_asc import SMART_ASA_GS
from utils import get_global_state, get_method, get_params


def smart_asa_create(
    _algod_client: algod.AlgodClient,
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

    params = get_params(_algod_client)
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
    _algod_client: algod.AlgodClient,
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    asset_id: int,
    caller: Account,
    save_abi_call: str = None,
) -> None:

    params = get_params(_algod_client)
    abi_call_fee = params.fee * 2

    caller.abi_call(
        get_method(smart_asa_contract, "asset_app_optin"),
        asset_id,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_config(
    _algod_client: algod.AlgodClient,
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

    global_state = get_global_state(_algod_client, smart_asa_app.app_id)

    if config_total is None:
        config_total = global_state[SMART_ASA_GS["total"].byte_str[1:-1]]
    if config_decimals is None:
        config_decimals = global_state[SMART_ASA_GS["decimals"].byte_str[1:-1]]
    if config_default_frozen is None:
        config_default_frozen = bool(
            global_state[SMART_ASA_GS["default_frozen"].byte_str[1:-1]]
        )
    if config_unit_name is None:
        config_unit_name = str(global_state[SMART_ASA_GS["unit_name"].byte_str[1:-1]])
    if config_asset_name is None:
        config_asset_name = str(global_state[SMART_ASA_GS["asset_name"].byte_str[1:-1]])
    if config_url is None:
        config_url = str(global_state[SMART_ASA_GS["url"].byte_str[1:-1]])
    if config_metadata_hash is None:
        config_metadata_hash = str(
            global_state[SMART_ASA_GS["metadata_hash"].byte_str[1:-1]]
        )
    if config_manager_addr is None:
        config_manager_addr = Account(
            address=encode_address(
                global_state[SMART_ASA_GS["manager_addr"].byte_str[1:-1]]
            )
        )
    if config_reserve_addr is None:
        config_reserve_addr = Account(
            address=encode_address(
                global_state[SMART_ASA_GS["reserve_addr"].byte_str[1:-1]]
            )
        )
    if config_freeze_addr is None:
        config_freeze_addr = Account(
            address=encode_address(
                global_state[SMART_ASA_GS["freeze_addr"].byte_str[1:-1]]
            )
        )
    if config_clawback_addr is None:
        config_clawback_addr = Account(
            address=encode_address(
                global_state[SMART_ASA_GS["clawback_addr"].byte_str[1:-1]]
            )
        )

    params = get_params(_algod_client)
    abi_call_fee = params.fee * 2

    manager.abi_call(
        get_method(smart_asa_contract, "asset_config"),
        smart_asa_id,
        config_total,
        config_decimals,
        config_default_frozen,
        config_unit_name,
        config_asset_name,
        config_url,
        config_metadata_hash,
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
    _algod_client: algod.AlgodClient,
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    xfer_asset: int,
    asset_amount: int,
    caller: Account,
    asset_receiver: Account,
    asset_sender: Optional[Account] = None,
    save_abi_call: str = None,
) -> None:

    params = get_params(_algod_client)
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
