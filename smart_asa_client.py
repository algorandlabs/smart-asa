from typing import Optional
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
    manager_addr: Optional[Account] = None,
    reserve_addr: Optional[Account] = None,
    freeze_addr: Optional[Account] = None,
    clawback_addr: Optional[Account] = None,
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
        manager_addr.address if manager_addr else creator.address,
        reserve_addr.address if manager_addr else creator.address,
        freeze_addr.address if manager_addr else creator.address,
        clawback_addr.address if manager_addr else creator.address,
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
    manager_addr: Optional[Account] = None,
    reserve_addr: Optional[Account] = None,
    freeze_addr: Optional[Account] = None,
    clawback_addr: Optional[Account] = None,
    save_abi_call: str = None,
) -> int:

    global_state = get_global_state(_algod_client, smart_asa_app.app_id)

    if not smart_asa_id:
        smart_asa_id = global_state[SMART_ASA_GS["Int"]["smart_asa_id"].byte_str[1:-1]]
    if not total:
        total = global_state[SMART_ASA_GS["Int"]["total"].byte_str[1:-1]]
    if not decimals:
        decimals = global_state[SMART_ASA_GS["Int"]["decimals"].byte_str[1:-1]]
    if not default_frozen:
        default_frozen = global_state[
            SMART_ASA_GS["Int"]["default_frozen"].byte_str[1:-1]
        ]
    if not unit_name:
        unit_name = global_state[SMART_ASA_GS["Bytes"]["unit_name"].byte_str[1:-1]]
    if not asset_name:
        asset_name = global_state[SMART_ASA_GS["Bytes"]["asset_name"].byte_str[1:-1]]
    if not url:
        url = global_state[SMART_ASA_GS["Bytes"]["url"].byte_str[1:-1]]
    if not metadata_hash:
        metadata_hash = global_state[
            SMART_ASA_GS["Bytes"]["metadata_hash"].byte_str[1:-1]
        ]
    if not manager_addr:
        manager_addr.address = global_state[
            SMART_ASA_GS["Bytes"]["manager_addr"].byte_str[1:-1]
        ]
    if not reserve_addr:
        reserve_addr.address = global_state[
            SMART_ASA_GS["Bytes"]["reserve_addr"].byte_str[1:-1]
        ]
    if not freeze_addr:
        freeze_addr.address = global_state[
            SMART_ASA_GS["Bytes"]["freeze_addr"].byte_str[1:-1]
        ]
    if not clawback_addr:
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
