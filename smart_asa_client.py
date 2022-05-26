"""
Smart ASA client
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

from typing import Optional, Union
from algosdk import algod
from algosdk.abi import Contract
from account import Account, AppAccount
from smart_asa_asc import SMART_ASA_GS
from utils import get_global_state, get_method, get_params


def smart_asa_create(
    _algod_client: algod.AlgodClient,
    smart_asa_app: AppAccount,
    creator: Account,
    smart_asa_contract: Contract,
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
        manager_addr if manager_addr is not None else creator.address,
        reserve_addr if reserve_addr is not None else creator.address,
        freeze_addr if freeze_addr is not None else creator.address,
        clawback_addr if clawback_addr is not None else creator.address,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )


def smart_asa_config(
    _algod_client: algod.AlgodClient,
    smart_asa_app: AppAccount,
    creator: Account,
    smart_asa_contract: Contract,
    smart_asa_id: int = None,
    total: int = None,
    decimals: int = None,
    default_frozen: bool = None,
    unit_name: str = None,
    asset_name: str = None,
    url: str = None,
    metadata_hash: str = None,
    manager_addr: Optional[Union[str, Account]] = None,
    reserve_addr: Optional[Union[str, Account]] = None,
    freeze_addr: Optional[Union[str, Account]] = None,
    clawback_addr: Optional[Union[str, Account]] = None,
    save_abi_call: str = None,
) -> int:

    global_state = get_global_state(_algod_client, smart_asa_app.app_id)

    if smart_asa_id is None:
        smart_asa_id = global_state[SMART_ASA_GS["Int"]["smart_asa_id"].byte_str[1:-1]]
    if total is None:
        total = global_state[SMART_ASA_GS["Int"]["total"].byte_str[1:-1]]
    if decimals is None:
        decimals = global_state[SMART_ASA_GS["Int"]["decimals"].byte_str[1:-1]]
    if default_frozen is None:
        default_frozen = global_state[
            SMART_ASA_GS["Int"]["default_frozen"].byte_str[1:-1]
        ]
    if unit_name is None:
        unit_name = global_state[SMART_ASA_GS["Bytes"]["unit_name"].byte_str[1:-1]]
    if asset_name is None:
        asset_name = global_state[SMART_ASA_GS["Bytes"]["asset_name"].byte_str[1:-1]]
    if url is None:
        url = global_state[SMART_ASA_GS["Bytes"]["url"].byte_str[1:-1]]
    if metadata_hash is None:
        metadata_hash = global_state[
            SMART_ASA_GS["Bytes"]["metadata_hash"].byte_str[1:-1]
        ]
    if manager_addr is None:
        manager_addr.address = global_state[
            SMART_ASA_GS["Bytes"]["manager_addr"].byte_str[1:-1]
        ]
    if reserve_addr is None:
        reserve_addr.address = global_state[
            SMART_ASA_GS["Bytes"]["reserve_addr"].byte_str[1:-1]
        ]
    if freeze_addr is None:
        freeze_addr.address = global_state[
            SMART_ASA_GS["Bytes"]["freeze_addr"].byte_str[1:-1]
        ]
    if clawback_addr is None:
        clawback_addr.address = global_state[
            SMART_ASA_GS["Bytes"]["clawback_addr"].byte_str[1:-1]
        ]

    params = get_params(_algod_client)
    abi_call_fee = params.fee * 2

    creator.abi_call(
        get_method(smart_asa_contract, "asset_config"),
        smart_asa_id,
        total,
        decimals,
        default_frozen,
        unit_name,
        asset_name,
        url,
        metadata_hash,
        manager_addr.address,
        reserve_addr.address,
        freeze_addr.address,
        clawback_addr.address,
        app=smart_asa_app,
        fee=abi_call_fee,
        save_abi_call=save_abi_call,
    )
    return smart_asa_id
