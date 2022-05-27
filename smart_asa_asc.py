#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart ASA PyTEAL reference implementation based on ARC-20
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

from pyteal import (
    App,
    Approve,
    Assert,
    AssetHolding,
    BareCallActions,
    Bytes,
    CallConfig,
    Concat,
    Expr,
    Global,
    If,
    InnerTxn,
    InnerTxnBuilder,
    Int,
    Itob,
    Len,
    Mode,
    Not,
    OnCompleteAction,
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

# / --- CONSTANTS
ADDRESS_BYTES_LENGTH = Int(32)

# / --- --- UNDERLYING ASA CONFIG
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
# / --- --- GLOBAL STATE
SMART_ASA_GLOBAL_INTS = {
    "total": Bytes("total"),
    "decimals": Bytes("decimals"),
    "default_frozen": Bytes("default_frozen"),
    "smart_asa_id": Bytes("smart_asa_id"),
    "global_frozen": Bytes("global_frozen"),  # TODO: treated as bool
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

SMART_ASA_GS = {**SMART_ASA_GLOBAL_INTS, **SMART_ASA_GLOBAL_BYTES}


smart_asa_global_state = StateSchema(
    num_uints=len(SMART_ASA_GLOBAL_INTS.keys()),
    num_byte_slices=len(SMART_ASA_GLOBAL_BYTES.keys()),
)

# / --- --- LOCAL STATE
SMART_ASA_LOCAL_INTS = {"frozen": Bytes("frozen")}

SMART_ASA_LOCAL_BYTES = {}

SMART_ASA_LS = {**SMART_ASA_LOCAL_INTS, **SMART_ASA_LOCAL_BYTES}

smart_asa_local_state = StateSchema(
    num_uints=len(SMART_ASA_LOCAL_INTS.keys()),
    num_byte_slices=len(SMART_ASA_LOCAL_BYTES.keys()),
)


# / --- --- SUBROUTINES
@Subroutine(TealType.uint64)
def underlying_asa_create_inner_tx() -> Expr:
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


@Subroutine(TealType.none)
def smart_asa_transfer_inner_txn(
    smart_asa_id: Expr,
    asset_amount: Expr,
    asset_sender: Expr,
    asset_receiver: Expr,
) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.fee: Int(0),
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: smart_asa_id,
                TxnField.asset_amount: asset_amount,
                TxnField.asset_sender: asset_sender,
                TxnField.asset_receiver: asset_receiver,
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def is_valid_address_bytes_length(address: Expr) -> Expr:
    # WARNING: Note this check only ensures proper bytes length on `address`,
    # but it doesn't ensure that those 32 bytes are a _proper_ Algorand
    # address.
    return Assert(Len(address) == ADDRESS_BYTES_LENGTH)


# / --- --- ABI
# / --- --- BARE CALLS
@Subroutine(TealType.none)
def asset_app_create() -> Expr:
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
        App.globalPut(SMART_ASA_GS["smart_asa_id"], Int(0)),
        App.globalPut(SMART_ASA_GS["total"], Int(0)),
        App.globalPut(SMART_ASA_GS["decimals"], Int(0)),
        App.globalPut(SMART_ASA_GS["default_frozen"], Int(0)),
        # NOTE: ASA behaves excluding `unit_name` field if not declared:
        App.globalPut(SMART_ASA_GS["unit_name"], Bytes("")),
        # NOTE: ASA behaves excluding `asset_name` field if not declared:
        App.globalPut(SMART_ASA_GS["asset_name"], Bytes("")),
        # NOTE: ASA behaves excluding `url` field if not declared:
        App.globalPut(SMART_ASA_GS["url"], Bytes("")),
        # NOTE: ASA behaves excluding `metadata_hash` field if not declared:
        App.globalPut(SMART_ASA_GS["metadata_hash"], Bytes("")),
        # TODO: should we initialize Smart ASA roles to App Creator?
        App.globalPut(SMART_ASA_GS["manager_addr"], Global.zero_address()),
        App.globalPut(SMART_ASA_GS["reserve_addr"], Global.zero_address()),
        App.globalPut(SMART_ASA_GS["freeze_addr"], Global.zero_address()),
        App.globalPut(SMART_ASA_GS["clawback_addr"], Global.zero_address()),
        # Special Smart ASA fields
        App.globalPut(SMART_ASA_GS["global_frozen"], Int(0)),
        Approve(),
    )


@Subroutine(TealType.none)
def on_closeout() -> Expr:
    # TODO: clawback all the account balance into the Smart ASA App
    return Reject()


@Subroutine(TealType.none)
def on_clear_state() -> Expr:
    # TODO: clawback all the account balance into the Smart ASA App
    return Reject()


smart_asa_abi = Router(
    "Smart ASA ref. implementation",
    BareCallActions(
        no_op=OnCompleteAction.create_only(asset_app_create()),
        # Rules governing a Smart ASA are only in place as long as the
        # controlling Smart Contract is not updatable.
        update_application=OnCompleteAction.always(Reject()),
        # Rules governing a Smart ASA are only in place as long as the
        # controlling Smart Contract is not deletable.
        delete_application=OnCompleteAction.always(Reject()),
        clear_state=OnCompleteAction.always(on_clear_state()),
        close_out=OnCompleteAction.always(on_closeout()),
    ),
)


# / --- --- METHODS
def asset_app_optin(asset_id: abi.Asset) -> Expr:
    # On OptIn the frozen status must be set to `True` if account owns any
    # units of the underlying ASA. This prevents malicious users to circumvent
    # the `default_frozen` status by clearing their Local State. Note that this
    # could be avoided by the use of Boxes once available.
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    is_correct_smart_asa_id = smart_asa_id == asset_id.get()
    default_frozen = App.globalGet(SMART_ASA_GS["default_frozen"])
    freeze_account = App.localPut(Txn.sender(), SMART_ASA_GS["default_frozen"], Int(1))
    account_balance = AssetHolding().balance(Txn.sender(), asset_id.get())
    # TODO: Underlying ASA opt-in and Smart ASA App opt-in could be atomic
    return Seq(
        # Preconditions
        Assert(smart_asa_id),
        Assert(is_correct_smart_asa_id),
        account_balance,
        # NOTE: Ref. imlp requires opt-in underlaying ASA to opt-in Smart ASA
        # App.
        Assert(account_balance.hasValue()),
        If(default_frozen, freeze_account),
        If(account_balance.value() > Int(0), freeze_account),
    )


# FIXME: in future release of ABI
smart_asa_abi.method(asset_app_optin, opt_in=CallConfig.ALL)


@smart_asa_abi.method
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

    is_creator = Txn.sender() == Global.creator_address()
    smart_asa_not_created = Not(App.globalGet(SMART_ASA_GS["smart_asa_id"]))
    smart_asa_id = underlying_asa_create_inner_tx()

    return Seq(
        # Preconditions
        Assert(is_creator),
        Assert(smart_asa_not_created),
        is_valid_address_bytes_length(manager_addr.get()),
        is_valid_address_bytes_length(reserve_addr.get()),
        is_valid_address_bytes_length(freeze_addr.get()),
        is_valid_address_bytes_length(clawback_addr.get()),
        # Underlying ASA creation
        App.globalPut(SMART_ASA_GS["smart_asa_id"], smart_asa_id),
        # Smart ASA properties
        App.globalPut(SMART_ASA_GS["total"], total.get()),
        App.globalPut(SMART_ASA_GS["decimals"], decimals.get()),
        App.globalPut(SMART_ASA_GS["default_frozen"], default_frozen.get()),
        App.globalPut(SMART_ASA_GS["unit_name"], unit_name.get()),
        App.globalPut(SMART_ASA_GS["asset_name"], asset_name.get()),
        App.globalPut(SMART_ASA_GS["url"], url.get()),
        App.globalPut(SMART_ASA_GS["metadata_hash"], metadata_hash.get()),
        App.globalPut(SMART_ASA_GS["manager_addr"], manager_addr.get()),
        App.globalPut(SMART_ASA_GS["reserve_addr"], reserve_addr.get()),
        App.globalPut(SMART_ASA_GS["freeze_addr"], freeze_addr.get()),
        App.globalPut(SMART_ASA_GS["clawback_addr"], clawback_addr.get()),
        output.set(App.globalGet(SMART_ASA_GS["smart_asa_id"])),
    )


@smart_asa_abi.method
def asset_config(
    config_asset: abi.Asset,
    total: abi.Uint64,  # NOTE: In ref. impl `total` can not be changed
    decimals: abi.Uint32,
    default_frozen: abi.Bool,  # NOTE: In ref. impl `default_frozen` can not be changed
    unit_name: abi.String,
    asset_name: abi.String,
    url: abi.String,
    metadata_hash: abi.String,  # FIXME: This was originally Byte in ARC-20
    manager_addr: abi.Address,
    reserve_addr: abi.Address,
    freeze_addr: abi.Address,
    clawback_addr: abi.Address,
) -> Expr:

    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    current_manager_addr = App.globalGet(SMART_ASA_GS["manager_addr"])
    current_freeze_addr = App.globalGet(SMART_ASA_GS["freeze_addr"])
    current_clawback_addr = App.globalGet(SMART_ASA_GS["clawback_addr"])

    is_manager = Txn.sender() == current_manager_addr
    is_correct_smart_asa_id = smart_asa_id == config_asset.get()

    update_freeze_addr = current_freeze_addr != freeze_addr.get()
    update_clawback_addr = current_clawback_addr != clawback_addr.get()

    return Seq(
        # Preconditions
        Assert(smart_asa_id),
        Assert(is_manager),
        Assert(
            is_correct_smart_asa_id
        ),  # NOTE: usless in ref. impl since 1 ASA : 1 App
        is_valid_address_bytes_length(manager_addr.get()),
        is_valid_address_bytes_length(reserve_addr.get()),
        is_valid_address_bytes_length(freeze_addr.get()),
        is_valid_address_bytes_length(clawback_addr.get()),
        If(update_freeze_addr).Then(
            Assert(current_freeze_addr != Global.zero_address())
        ),
        If(update_clawback_addr).Then(
            Assert(current_clawback_addr != Global.zero_address())
        ),
        # Smart ASA properties
        # NOTE: In ref. impl `total` can not be changed
        App.globalPut(SMART_ASA_GS["decimals"], decimals.get()),
        # NOTE: In ref. impl `default_frozen` can not be changed
        App.globalPut(SMART_ASA_GS["unit_name"], unit_name.get()),
        App.globalPut(SMART_ASA_GS["asset_name"], asset_name.get()),
        App.globalPut(SMART_ASA_GS["url"], url.get()),
        App.globalPut(SMART_ASA_GS["metadata_hash"], metadata_hash.get()),
        App.globalPut(SMART_ASA_GS["manager_addr"], manager_addr.get()),
        App.globalPut(SMART_ASA_GS["reserve_addr"], reserve_addr.get()),
        App.globalPut(SMART_ASA_GS["freeze_addr"], freeze_addr.get()),
        App.globalPut(SMART_ASA_GS["clawback_addr"], clawback_addr.get()),
    )


@smart_asa_abi.method
def asset_transfer(
    xfer_asset: abi.Asset,
    asset_amount: abi.Uint64,
    asset_sender: abi.Account,
    asset_receiver: abi.Account,
) -> Expr:
    # TODO: Consider adding a special case for miniting
    # TODO: Ref. implementation could have an `asset_mint` method
    #   which can put up to `total` units of Smart ASA in circulation.
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    clawback_addr = App.globalGet(SMART_ASA_GS["clawback_addr"])
    is_not_clawback = Txn.sender() != clawback_addr
    is_creator = Txn.sender() == Global.creator_address()
    is_correct_smart_asa_id = smart_asa_id == xfer_asset.get()
    receiver_is_optedin = App.optedIn(
        asset_receiver.get(), Global.current_application_id()
    )
    global_frozen = App.globalGet(SMART_ASA_GS["global_frozen"])
    asset_sender_frozen = App.localGet(asset_sender.get(), SMART_ASA_LS["frozen"])
    asset_receiver_frozen = App.localGet(asset_receiver.get(), SMART_ASA_LS["frozen"])
    return Seq(
        # Preconditions
        is_valid_address_bytes_length(asset_sender.get()),
        is_valid_address_bytes_length(asset_receiver.get()),
        Assert(is_correct_smart_asa_id),
        Assert(receiver_is_optedin),  # NOTE: if Smart ASA requires Local State
        If(is_not_clawback)
        .Then(
            Seq(
                # Asset Regular Transfer Preconditions
                Assert(Txn.sender() == Txn.accounts[asset_sender.get()]),
                Assert(Not(global_frozen)),
                Assert(Not(asset_sender_frozen)),
                Assert(Not(asset_receiver_frozen)),
            )
        )
        .ElseIf(is_creator)
        .Then(
            # Asset Minting Preconditions
            # NOTE: The minting premission is granted to `creator`, instead of
            # `manager`, because a Smart ASA could be created with no
            # `manager`, resulting in a locked-in Smart ASA.
            Assert(
                Global.current_application_address() == Txn.accounts[asset_sender.get()]
            )
        ),
        smart_asa_transfer_inner_txn(
            smart_asa_id,
            asset_amount.get(),
            Txn.accounts[asset_sender.get()],
            Txn.accounts[asset_receiver.get()],
        ),
    )


@smart_asa_abi.method
def asset_freeze(
    freeze_asset: abi.Uint64,  # FIXME: this should be Ref. type abi.Asset
    asset_frozen: abi.Bool,
) -> Expr:
    # TODO: Add a boolean flag to the state
    return Reject()


@smart_asa_abi.method
def account_freeze(
    freeze_asset: abi.Uint64,  # FIXME: this should be Ref. type abi.Asset
    freeze_account: abi.Address,  # FIXME: this should be Ref. type abi.Account
    asset_frozen: abi.Bool,
) -> Expr:
    return Reject()


@smart_asa_abi.method
def asset_destroy(
    destroy_asset: abi.Uint64,  # FIXME: this should be Ref. type abi.Asset
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
