#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart ASA PyTEAL reference implementation based on ARC-20
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

from pyteal import (
    ABIReturnSubroutine,
    App,
    Approve,
    Assert,
    Bytes,
    Concat,
    Expr,
    Global,
    InnerTxn,
    InnerTxnBuilder,
    Int,
    Itob,
    Mode,
    Not,
    OnComplete,
    OptimizeOptions,
    Reject,
    Return,
    Router,
    Seq,
    Subroutine,
    TealType,
    Txn,
    TxnField,
    TxnType,
    abi,
    compileTeal,
)
from algosdk.future.transaction import StateSchema

TEAL_VERSION = 6


# UNDERLYING ASA CONFIG
UNDERLYING_ASA_TOTAL = Int(2**64 - 1)
UNDERLYING_ASA_DECIMALS = Int(0)
UNDERLYING_ASA_DEFAULT_FROZEN = Int(1)
UNDERLYING_ASA_UNIT_NAME = Bytes("S-ASA")
UNDERLYING_ASA_NAME = Bytes("SMART-ASA")
UNDERLYING_ASA_URL = Concat(
    Bytes("smart-asa-app-id:"), Itob(Global.current_application_id())
)
UNDERLYING_ASA_METADATA_HASH = Bytes("")
UNDERLYING_ASA_MANAGER_ADDR = Global.current_application_address()
UNDERLYING_ASA_RESERVE_ADDR = Global.current_application_address()
UNDERLYING_ASA_FREEZE_ADDR = Global.current_application_address()
UNDERLYING_ASA_CLAWBACK_ADDR = Global.current_application_address()


# / --- SMART ASA ASC
# / --- --- STATE
SMART_ASA_GLOBAL_INTS = {
    "total": Bytes("total"),
    "decimals": Bytes("decimals"),
    "default_frozen": Bytes("default_frozen"),
    "smart_asa_id": Bytes("smart_asa_id"),
}

SMART_ASA_GLOBAL_BYTES = {
    "unit_name": Bytes("unit_name"),
    "asset_name": Bytes("asset_name"),
    "url": Bytes("url"),
    "metadata_hash": Bytes("metadata_hash"),
    "manager_addr": Bytes("manager_addr"),
    "reserve_addr": Bytes("reserve_addr"),
    "freeze_addr": Bytes("freeze_addr"),
    "clawback_addr": Bytes("clawback_addr"),
}

SMART_ASA_GS = {
    "Int": SMART_ASA_GLOBAL_INTS,
    "Bytes": SMART_ASA_GLOBAL_BYTES,
}


smart_asa_global_state = StateSchema(
    num_uints=len(SMART_ASA_GS["Int"].keys()),
    num_byte_slices=len(SMART_ASA_GS["Bytes"].keys()),
)

smart_asa_local_state = StateSchema(
    num_uints=0,
    num_byte_slices=0,
)


# / --- --- SUBROUTINES
@Subroutine(TealType.uint64)
def underlay_asa_create_inner_tx() -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.fee: Int(0),
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: UNDERLYING_ASA_TOTAL,
                TxnField.config_asset_decimals: UNDERLYING_ASA_DECIMALS,
                TxnField.config_asset_default_frozen: UNDERLYING_ASA_DEFAULT_FROZEN,
                TxnField.config_asset_unit_name: UNDERLYING_ASA_UNIT_NAME,
                TxnField.config_asset_name: UNDERLYING_ASA_NAME,
                TxnField.config_asset_url: UNDERLYING_ASA_URL,
                TxnField.config_asset_manager: UNDERLYING_ASA_MANAGER_ADDR,
                TxnField.config_asset_reserve: UNDERLYING_ASA_RESERVE_ADDR,
                TxnField.config_asset_freeze: UNDERLYING_ASA_FREEZE_ADDR,
                TxnField.config_asset_clawback: UNDERLYING_ASA_CLAWBACK_ADDR,
            }
        ),
        InnerTxnBuilder.Submit(),
        Return(InnerTxn.created_asset_id()),
    )


# / --- --- ABI
smart_asa_abi = Router("Smart ASA ref. implementation")


# / --- --- BARE CALLS
def on_create() -> Expr:
    return Seq(
        # Preconditions
        # Not mandatory - Smart ASA Application self validate its state.
        Assert(Txn.global_num_uints() == Int(smart_asa_global_state.num_uints)),
        Assert(
            Txn.global_num_byte_slices() == Int(smart_asa_global_state.num_byte_slices)
        ),
        Assert(Txn.local_num_uints() == Int(smart_asa_local_state.num_uints)),
        Assert(
            Txn.local_num_byte_slices() == Int(smart_asa_local_state.num_byte_slices)
        ),
        # Init Smart ASA ID
        App.globalPut(SMART_ASA_GS["Int"]["smart_asa_id"], Int(0)),
        Approve(),
    )


def on_optin() -> Expr:
    # If Smart ASA could be frozen (Freeze Address not null) then on OptIn the
    # frozen status must be set to True in account owns the underlying ASA.
    # This prevents malicious users to circumvent the frozen status by clearing
    # their Local State. Note that this could be avoided by the use of Boxes
    # once available.
    # TODO: add OptIn logic
    return Reject()


def on_closeout() -> Expr:
    return Reject()


def on_clear_state() -> Expr:
    return Reject()


def on_update() -> Expr:
    # Rules governing a Smart ASA are only in place as long as the controlling
    # Smart Contract is not updatable.
    return Reject()


def on_delete() -> Expr:
    # Rules governing a Smart ASA are only in place as long as the controlling
    # Smart Contract is not deletable.
    return Reject()


smart_asa_abi.add_bare_call(on_create(), OnComplete.NoOp, creation=True)
smart_asa_abi.add_bare_call(on_optin(), OnComplete.OptIn)
smart_asa_abi.add_bare_call(on_closeout(), OnComplete.CloseOut)
smart_asa_abi.add_bare_call(on_clear_state(), OnComplete.ClearState)
smart_asa_abi.add_bare_call(on_update(), OnComplete.UpdateApplication)
smart_asa_abi.add_bare_call(on_delete(), OnComplete.DeleteApplication)


# / --- --- METHODS
@smart_asa_abi.add_method_handler
@ABIReturnSubroutine
def asset_create(
    total: abi.Uint64,
    decimals: abi.Uint32,
    default_frozen: abi.Bool,
    unit_name: abi.String,
    asset_name: abi.String,
    url: abi.String,
    metadata_hash: abi.String,  # FIXME: This was originally Byte in ARC-20
    manager_addr: abi.Address,
    reserve_addr: abi.Address,
    freeze_addr: abi.Address,
    clawback_addr: abi.Address,
    *,
    output: abi.Uint64,
) -> Expr:

    smart_asa_not_created = Not(App.globalGet(SMART_ASA_GS["Int"]["smart_asa_id"]))
    smart_asa_id = underlay_asa_create_inner_tx()

    return Seq(
        # Preconditions
        Assert(Txn.sender() == Global.creator_address()),
        Assert(smart_asa_not_created),
        # Underlying ASA creation
        App.globalPut(SMART_ASA_GS["Int"]["smart_asa_id"], smart_asa_id),
        # Smart ASA properties
        App.globalPut(SMART_ASA_GS["Int"]["total"], total.get()),
        # NOTE: As ref. implementation we could have an `asset_mint` method
        # which can put up to `total` units of Smart ASA in circulation.
        App.globalPut(SMART_ASA_GS["Int"]["decimals"], decimals.get()),
        App.globalPut(SMART_ASA_GS["Int"]["default_frozen"], default_frozen.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["unit_name"], unit_name.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["asset_name"], asset_name.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["url"], url.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["metadata_hash"], metadata_hash.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["manager_addr"], manager_addr.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["reserve_addr"], reserve_addr.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["freeze_addr"], freeze_addr.get()),
        App.globalPut(SMART_ASA_GS["Bytes"]["clawback_addr"], clawback_addr.get()),
        output.set(App.globalGet(SMART_ASA_GS["Int"]["smart_asa_id"])),
    )


@smart_asa_abi.add_method_handler
@ABIReturnSubroutine
def asset_config(
    config_asset: abi.Uint64,  # NOTE: this should be type abi.Asset
    total: abi.Uint64,
    decimals: abi.Uint32,
    default_frozen: abi.Bool,
    unit_name: abi.String,
    asset_name: abi.String,
    url: abi.String,
    metadata_hash: abi.Byte,  # FIXME: This was originally Byte in ARC-20
    manager_addr: abi.Address,
    reserve_addr: abi.Address,
    freeze_addr: abi.Address,
    clawback_addr: abi.Address,
) -> Expr:
    return Reject()


@smart_asa_abi.add_method_handler
@ABIReturnSubroutine
def asset_transfer(
    xfer_asset: abi.Uint64,  # NOTE: this should be type abi.Asset
    asset_amount: abi.Uint64,
    asset_sender: abi.Address,  # NOTE: this should be type abi.Account
    asset_receiver: abi.Address,  # NOTE: this should be type abi.Account
) -> Expr:
    return Reject()


@smart_asa_abi.add_method_handler
@ABIReturnSubroutine
def asset_freeze(
    freeze_asset: abi.Uint64,  # NOTE: this should be type abi.Asset
    asset_frozen: abi.Bool,
) -> Expr:
    return Reject()


@smart_asa_abi.add_method_handler
@ABIReturnSubroutine
def account_freeze(
    freeze_asset: abi.Uint64,  # NOTE: this should be type abi.Asset
    freeze_account: abi.Address,  # NOTE: this should be type abi.Account
    asset_frozen: abi.Bool,
) -> Expr:
    return Reject()


@smart_asa_abi.add_method_handler
@ABIReturnSubroutine
def asset_destroy(
    destroy_asset: abi.Uint64,  # NOTE: this should be type abi.Asset
) -> Expr:
    return Reject()


def compile_stateful(program: Expr) -> str:
    return compileTeal(
        program,
        Mode.Application,
        version=TEAL_VERSION,
        assembleConstants=True,
        optimize=OptimizeOptions(scratch_slots=True),
    )


def compile_stateless(program: Expr) -> str:
    return compileTeal(
        program,
        Mode.Signature,
        version=TEAL_VERSION,
        assembleConstants=True,
        optimize=OptimizeOptions(scratch_slots=True),
    )


if __name__ == "__main__":
    # Allow quickly testing compilation.
    from smart_asa_test import test_compile

    test_compile(*smart_asa_abi.build_program())
