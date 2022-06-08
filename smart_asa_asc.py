#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart ASA PyTEAL reference implementation based on ARC-20
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

from pyteal import (
    And,
    App,
    Approve,
    Assert,
    AssetHolding,
    BareCallActions,
    Bytes,
    CallConfig,
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
    Or,
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

# NOTE: The following costs could change over time with protocol upgrades.
OPTIN_COST = Int(100_000)
UINTS_COST = Int(28_500)
BYTES_COST = Int(50_000)

# / --- --- UNDERLYING ASA CONFIG
UNDERLYING_ASA_TOTAL = Int(2**64 - 1)
UNDERLYING_ASA_DECIMALS = Int(0)
UNDERLYING_ASA_DEFAULT_FROZEN = Int(1)
UNDERLYING_ASA_UNIT_NAME = Bytes("S-ASA")
UNDERLYING_ASA_NAME = Bytes("SMART-ASA")
# FIXME
# UNDERLYING_ASA_URL = Concat(
#     Bytes("smart-asa-app-id:"), Itob(Global.current_application_id())
# )
UNDERLYING_ASA_URL = Itob(Global.current_application_id())
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
    "frozen": Bytes("frozen"),
}

SMART_ASA_GLOBAL_BYTES = {
    "unit_name": Bytes("unit_name"),
    "name": Bytes("name"),
    "url": Bytes("url"),
    "metadata_hash": Bytes("metadata_hash"),
    "manager_addr": Bytes("manager_addr"),
    "reserve_addr": Bytes("reserve_addr"),
    "freeze_addr": Bytes("freeze_addr"),
    "clawback_addr": Bytes("clawback_addr"),
}

SMART_ASA_GS = {**SMART_ASA_GLOBAL_INTS, **SMART_ASA_GLOBAL_BYTES}


smart_asa_global_state = StateSchema(
    num_uints=len(SMART_ASA_GLOBAL_INTS),
    num_byte_slices=len(SMART_ASA_GLOBAL_BYTES),
)

# / --- --- LOCAL STATE
# NOTE: Local State is needed only if the Smart ASA has `account_frozen`.
# Local State is not needed in case Smart ASA has just "global" `asset_freeze`.
SMART_ASA_LOCAL_INTS = {
    "smart_asa_id": Bytes("smart_asa_id"),
    "frozen": Bytes("frozen"),
}

SMART_ASA_LOCAL_BYTES = {}

SMART_ASA_LS = {**SMART_ASA_LOCAL_INTS, **SMART_ASA_LOCAL_BYTES}

smart_asa_local_state = StateSchema(
    num_uints=len(SMART_ASA_LOCAL_INTS.keys()),
    num_byte_slices=len(SMART_ASA_LOCAL_BYTES.keys()),
)


# / --- --- SUBROUTINES
@Subroutine(TealType.none)
def init_global_state() -> Expr:
    return Seq(
        App.globalPut(SMART_ASA_GS["smart_asa_id"], Int(0)),
        App.globalPut(SMART_ASA_GS["total"], Int(0)),
        App.globalPut(SMART_ASA_GS["decimals"], Int(0)),
        App.globalPut(SMART_ASA_GS["default_frozen"], Int(0)),
        # NOTE: ASA behaves excluding `unit_name` field if not declared:
        App.globalPut(SMART_ASA_GS["unit_name"], Bytes("")),
        # NOTE: ASA behaves excluding `name` field if not declared:
        App.globalPut(SMART_ASA_GS["name"], Bytes("")),
        # NOTE: ASA behaves excluding `url` field if not declared:
        App.globalPut(SMART_ASA_GS["url"], Bytes("")),
        # NOTE: ASA behaves excluding `metadata_hash` field if not declared:
        App.globalPut(SMART_ASA_GS["metadata_hash"], Bytes("")),
        App.globalPut(SMART_ASA_GS["manager_addr"], Global.zero_address()),
        App.globalPut(SMART_ASA_GS["reserve_addr"], Global.zero_address()),
        App.globalPut(SMART_ASA_GS["freeze_addr"], Global.zero_address()),
        App.globalPut(SMART_ASA_GS["clawback_addr"], Global.zero_address()),
        # Special Smart ASA fields
        App.globalPut(SMART_ASA_GS["frozen"], Int(0)),
    )


@Subroutine(TealType.none)
def init_local_state() -> Expr:
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    return Seq(
        App.localPut(Txn.sender(), SMART_ASA_LS["smart_asa_id"], smart_asa_id),
        App.localPut(Txn.sender(), SMART_ASA_LS["frozen"], Int(0)),
    )


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
def smart_asa_destroy_inner_txn(smart_asa_id: Expr) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.fee: Int(0),
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset: smart_asa_id,
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def is_valid_address_bytes_length(address: Expr) -> Expr:
    # WARNING: Note this check only ensures proper bytes' length on `address`,
    # but doesn't ensure that those 32 bytes are a _proper_ Algorand address.
    return Assert(Len(address) == ADDRESS_BYTES_LENGTH)


@Subroutine(TealType.uint64)
def circulating_supply(asset_id: Expr):
    smart_asa_reserve = AssetHolding.balance(
        Global.current_application_address(), asset_id
    )
    return Seq(smart_asa_reserve, UNDERLYING_ASA_TOTAL - smart_asa_reserve.value())


@Subroutine(TealType.none)
def getter_preconditions(asset_id: Expr) -> Expr:
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    is_correct_smart_asa_id = smart_asa_id == asset_id
    return Seq(
        Assert(smart_asa_id),
        Assert(is_correct_smart_asa_id),
    )


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
        init_global_state(),
        Approve(),
    )


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
        clear_state=OnCompleteAction.always(Reject()),
    ),
)


# / --- --- METHODS
@smart_asa_abi.method(opt_in=CallConfig.ALL)
def asset_app_optin(asset_id: abi.Asset) -> Expr:
    # TODO: Underlying ASA and Smart ASA App opt-in could be atomic.
    # On OptIn the frozen status must be set to `True` if account owns any
    # units of the underlying ASA. This prevents malicious users to circumvent
    # the `default_frozen` status by clearing their Local State. Note that this
    # could be avoided by the use of Boxes once available.
    asset_id = Txn.assets[asset_id.get()]
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    is_correct_smart_asa_id = smart_asa_id == asset_id
    default_frozen = App.globalGet(SMART_ASA_GS["default_frozen"])
    freeze_account = App.localPut(Txn.sender(), SMART_ASA_LS["frozen"], Int(1))
    account_balance = AssetHolding().balance(Txn.sender(), asset_id)
    optin_to_underlying_asa = account_balance.hasValue()
    return Seq(
        # Preconditions
        Assert(smart_asa_id),
        Assert(is_correct_smart_asa_id),
        account_balance,
        Assert(optin_to_underlying_asa),
        # Effects
        init_local_state(),
        If(Or(default_frozen, account_balance.value() > Int(0)), freeze_account),
        Approve(),
    )


@smart_asa_abi.method(close_out=CallConfig.ALL)
def asset_app_closeout(asset_id: abi.Asset) -> Expr:
    # TODO: Underlying ASA and Smart ASA App close-out could be atomic.
    asset_id = Txn.assets[asset_id.get()]
    current_smart_asa_id = App.localGet(Txn.sender(), SMART_ASA_LS["smart_asa_id"])
    is_correct_smart_asa_id = current_smart_asa_id == asset_id
    account_balance = AssetHolding().balance(Txn.sender(), asset_id)
    optin_to_underlying_asa = account_balance.hasValue()
    return Seq(
        # Preconditions
        # NOTE: Smart ASA existence is not checked on close-out since
        # would be impossible to close-out destroyed assets.
        Assert(is_correct_smart_asa_id),
        account_balance,
        Assert(Not(optin_to_underlying_asa)),
        # Effects
        Approve(),
    )


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
        Assert(total.get() > Int(0)),  # NOTE: Ref. imlp requires `total` > 0
        is_valid_address_bytes_length(manager_addr.get()),
        is_valid_address_bytes_length(reserve_addr.get()),
        is_valid_address_bytes_length(freeze_addr.get()),
        is_valid_address_bytes_length(clawback_addr.get()),
        # Effects
        # Underlying ASA creation
        App.globalPut(SMART_ASA_GS["smart_asa_id"], smart_asa_id),
        # Smart ASA properties
        App.globalPut(SMART_ASA_GS["total"], total.get()),
        App.globalPut(SMART_ASA_GS["decimals"], decimals.get()),
        App.globalPut(SMART_ASA_GS["default_frozen"], default_frozen.get()),
        App.globalPut(SMART_ASA_GS["unit_name"], unit_name.get()),
        App.globalPut(SMART_ASA_GS["name"], asset_name.get()),
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
) -> Expr:

    config_asset = Txn.assets[config_asset.get()]
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    current_manager_addr = App.globalGet(SMART_ASA_GS["manager_addr"])
    current_reserve_addr = App.globalGet(SMART_ASA_GS["reserve_addr"])
    current_freeze_addr = App.globalGet(SMART_ASA_GS["freeze_addr"])
    current_clawback_addr = App.globalGet(SMART_ASA_GS["clawback_addr"])

    is_manager_addr = Txn.sender() == current_manager_addr
    is_correct_smart_asa_id = smart_asa_id == config_asset

    update_reserve_addr = current_reserve_addr != reserve_addr.get()
    update_freeze_addr = current_freeze_addr != freeze_addr.get()
    update_clawback_addr = current_clawback_addr != clawback_addr.get()

    # NOTE: In ref. implementation Smart ASA total can not be configured to
    # less than its current circulating supply.
    is_valid_total = total.get() >= circulating_supply(smart_asa_id)

    return Seq(
        # Preconditions
        Assert(smart_asa_id),
        Assert(
            is_correct_smart_asa_id
        ),  # NOTE: usless in ref. impl since 1 ASA : 1 App
        is_valid_address_bytes_length(manager_addr.get()),
        is_valid_address_bytes_length(reserve_addr.get()),
        is_valid_address_bytes_length(freeze_addr.get()),
        is_valid_address_bytes_length(clawback_addr.get()),
        Assert(is_manager_addr),
        If(update_reserve_addr).Then(
            Assert(current_reserve_addr != Global.zero_address())
        ),
        If(update_freeze_addr).Then(
            Assert(current_freeze_addr != Global.zero_address())
        ),
        If(update_clawback_addr).Then(
            Assert(current_clawback_addr != Global.zero_address())
        ),
        Assert(is_valid_total),
        # Effects
        App.globalPut(SMART_ASA_GS["total"], total.get()),
        App.globalPut(SMART_ASA_GS["decimals"], decimals.get()),
        App.globalPut(SMART_ASA_GS["default_frozen"], default_frozen.get()),
        App.globalPut(SMART_ASA_GS["unit_name"], unit_name.get()),
        App.globalPut(SMART_ASA_GS["name"], asset_name.get()),
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
    xfer_asset = Txn.assets[xfer_asset.get()]
    asset_sender = Txn.accounts[asset_sender.get()]
    asset_receiver = Txn.accounts[asset_receiver.get()]
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    clawback_addr = App.globalGet(SMART_ASA_GS["clawback_addr"])
    is_not_clawback = And(
        Txn.sender() == asset_sender,
        Txn.sender() != clawback_addr,
    )

    # NOTE: Ref. implementation grants _minting_ premission to `reserve_addr`,
    # has restriction no restriction on who is the minting _receiver_.
    # WARNING: Setting Smart ASA `reserve` to ZERO_ADDRESS switchs-off minting.
    is_minting = And(
        Txn.sender() == App.globalGet(SMART_ASA_GS["reserve_addr"]),
        Global.current_application_address() == asset_sender,
    )

    # NOTE: Ref. implementation grants _burning_ premission to `reserve_addr`,
    # has restriction both on burning _sender_ and _receiver_ to prevent
    # _clawback_ throug burning.
    # WARNING: Setting Smart ASA `reserve` to ZERO_ADDRESS switchs-off burning.
    is_burning = And(
        Txn.sender() == App.globalGet(SMART_ASA_GS["reserve_addr"]),
        App.globalGet(SMART_ASA_GS["reserve_addr"]) == asset_sender,
        Global.current_application_address() == asset_receiver,
    )

    is_clawback = Txn.sender() == clawback_addr
    is_correct_smart_asa_id = smart_asa_id == xfer_asset

    # NOTE: Ref. implementation checks that `smart_asa_id` is correct in Local
    # State since the App could generate a new Smart ASA (if the previous one
    # has been dystroied) requiring users to opt-in again to gain a coherent
    # new `frozen` status.
    is_current_smart_asa_id = And(
        smart_asa_id == App.localGet(asset_sender, SMART_ASA_LS["smart_asa_id"]),
        smart_asa_id == App.localGet(asset_receiver, SMART_ASA_LS["smart_asa_id"]),
    )

    receiver_is_optedin = App.optedIn(asset_receiver, Global.current_application_id())
    asset_frozen = App.globalGet(SMART_ASA_GS["frozen"])
    asset_sender_frozen = App.localGet(asset_sender, SMART_ASA_LS["frozen"])
    asset_receiver_frozen = App.localGet(asset_receiver, SMART_ASA_LS["frozen"])
    return Seq(
        # Preconditions
        Assert(smart_asa_id),
        Assert(is_correct_smart_asa_id),
        is_valid_address_bytes_length(asset_sender),
        is_valid_address_bytes_length(asset_receiver),
        If(is_not_clawback)
        .Then(
            Seq(
                # Asset Regular Transfer Preconditions
                Assert(receiver_is_optedin),  # NOTE: if Smart ASA requires Local State
                Assert(Not(asset_frozen)),
                Assert(Not(asset_sender_frozen)),
                Assert(Not(asset_receiver_frozen)),
                Assert(is_current_smart_asa_id),
            )
        )
        .ElseIf(is_minting)
        .Then(
            Seq(
                # Asset Minting Preconditions
                Assert(receiver_is_optedin),  # NOTE: if Smart ASA requires Local State
                Assert(Not(asset_frozen)),
                Assert(Not(asset_receiver_frozen)),
                Assert(
                    smart_asa_id
                    == App.localGet(asset_receiver, SMART_ASA_LS["smart_asa_id"])
                ),
                # NOTE: Ref. implementation prevents minting more than `total`.
                Assert(
                    circulating_supply(smart_asa_id) + asset_amount.get()
                    <= App.globalGet(SMART_ASA_GS["total"])
                ),
            )
        )
        .ElseIf(is_burning)
        .Then(
            Seq(
                # Asset Burning Preconditions
                Assert(Not(asset_frozen)),
                Assert(Not(asset_sender_frozen)),
            )
        )
        .Else(
            Seq(
                Assert(is_clawback),
                Assert(is_current_smart_asa_id),
                Assert(receiver_is_optedin),  # NOTE: if Smart ASA requires Local State
            )
        ),
        # Effects
        smart_asa_transfer_inner_txn(
            xfer_asset,
            asset_amount.get(),
            asset_sender,
            asset_receiver,
        ),
    )


@smart_asa_abi.method
def asset_freeze(freeze_asset: abi.Asset, asset_frozen: abi.Bool) -> Expr:
    freeze_asset = Txn.assets[freeze_asset.get()]
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    is_correct_smart_asa_id = smart_asa_id == freeze_asset
    is_freeze_addr = Txn.sender() == App.globalGet(SMART_ASA_GS["freeze_addr"])
    is_boolean = Or(asset_frozen.get() == Int(0), asset_frozen.get() == Int(1))
    return Seq(
        # Asset Freeze Preconditions
        Assert(smart_asa_id),
        Assert(is_correct_smart_asa_id),
        Assert(is_boolean),
        Assert(is_freeze_addr),
        # Effects
        App.globalPut(SMART_ASA_GS["frozen"], asset_frozen.get()),
    )


@smart_asa_abi.method
def account_freeze(
    freeze_asset: abi.Asset,
    freeze_account: abi.Account,
    asset_frozen: abi.Bool,
) -> Expr:
    freeze_asset = Txn.assets[freeze_asset.get()]
    freeze_account = Txn.accounts[freeze_account.get()]
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    is_correct_smart_asa_id = smart_asa_id == freeze_asset
    is_freeze_addr = Txn.sender() == App.globalGet(SMART_ASA_GS["freeze_addr"])
    is_boolean = Or(asset_frozen.get() == Int(0), asset_frozen.get() == Int(1))
    return Seq(
        # Account Freeze Preconditions
        Assert(smart_asa_id),
        Assert(is_correct_smart_asa_id),
        is_valid_address_bytes_length(freeze_account),
        Assert(is_boolean),
        Assert(is_freeze_addr),
        # Effects
        App.localPut(freeze_account, SMART_ASA_LS["frozen"], asset_frozen.get()),
    )


@smart_asa_abi.method
def asset_destroy(destroy_asset: abi.Asset) -> Expr:
    destroy_asset = Txn.assets[destroy_asset.get()]
    smart_asa_id = App.globalGet(SMART_ASA_GS["smart_asa_id"])
    is_correct_smart_asa_id = smart_asa_id == destroy_asset
    is_manager_addr = Txn.sender() == App.globalGet(SMART_ASA_GS["manager_addr"])
    return Seq(
        # Asset Destroy Preconditions
        Assert(smart_asa_id),
        Assert(is_correct_smart_asa_id),
        Assert(is_manager_addr),
        # Effects
        smart_asa_destroy_inner_txn(destroy_asset),
        init_global_state(),
    )


# / --- --- GETTERS
@smart_asa_abi.method
def is_asset_frozen(freeze_asset: abi.Asset, *, output: abi.Bool) -> Expr:
    freeze_asset = Txn.assets[freeze_asset.get()]
    return Seq(
        # Preconditions
        getter_preconditions(freeze_asset),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["frozen"])),
    )


@smart_asa_abi.method
def is_account_frozen(
    freeze_asset: abi.Asset, freeze_account: abi.Account, *, output: abi.Bool
) -> Expr:
    freeze_asset = Txn.assets[freeze_asset.get()]
    freeze_account = Txn.accounts[freeze_account.get()]
    return Seq(
        # Preconditions
        getter_preconditions(freeze_asset),
        is_valid_address_bytes_length(freeze_account),
        # Effects
        output.set(App.localGet(freeze_account, SMART_ASA_LS["frozen"])),
    )


@smart_asa_abi.method
def get_total(asset_id: abi.Asset, *, output: abi.Uint64) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["total"])),
    )


@smart_asa_abi.method
def get_decimals(asset_id: abi.Asset, *, output: abi.Uint32) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["decimals"])),
    )


@smart_asa_abi.method
def get_default_frozen(asset_id: abi.Asset, *, output: abi.Bool) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["default_frozen"])),
    )


@smart_asa_abi.method
def get_unit_name(asset_id: abi.Asset, *, output: abi.String) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["unit_name"])),
    )


@smart_asa_abi.method
def get_asset_name(asset_id: abi.Asset, *, output: abi.String) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["name"])),
    )


@smart_asa_abi.method
def get_url(asset_id: abi.Asset, *, output: abi.String) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["url"])),
    )


@smart_asa_abi.method
def get_metadata_hash(
    asset_id: abi.Asset,
    *,
    output: abi.String,  # FIXME: This was originally Byte in ARC-20
) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["metadata_hash"])),
    )


@smart_asa_abi.method
def get_manager_addr(asset_id: abi.Asset, *, output: abi.Address) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["manager_addr"])),
    )


@smart_asa_abi.method
def get_reserve_addr(asset_id: abi.Asset, *, output: abi.Address) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["reserve_addr"])),
    )


@smart_asa_abi.method
def get_freeze_addr(asset_id: abi.Asset, *, output: abi.Address) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["freeze_addr"])),
    )


@smart_asa_abi.method
def get_clawback_addr(asset_id: abi.Asset, *, output: abi.Address) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(App.globalGet(SMART_ASA_GS["clawback_addr"])),
    )


@smart_asa_abi.method
def get_circulating_supply(asset_id: abi.Asset, *, output: abi.Uint64) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(circulating_supply(asset_id)),
    )


@smart_asa_abi.method
def get_optin_min_balance(asset_id: abi.Asset, *, output: abi.Uint64) -> Expr:
    asset_id = Txn.assets[asset_id.get()]
    local_uints = Int(smart_asa_local_state.num_uints)
    local_bytes = Int(smart_asa_local_state.num_byte_slices)
    min_balance = OPTIN_COST + UINTS_COST * local_uints + BYTES_COST * local_bytes
    return Seq(
        # Preconditions
        getter_preconditions(asset_id),
        # Effects
        output.set(min_balance),
    )


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
