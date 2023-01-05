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
    AssetParam,
    BareCallActions,
    Bytes,
    CallConfig,
    Concat,
    Expr,
    Extract,
    Global,
    Gtxn,
    If,
    InnerTxn,
    InnerTxnBuilder,
    Int,
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
    Suffix,
    TealType,
    Txn,
    TxnField,
    TxnType,
    abi,
    compileTeal,
)
from algosdk.future.transaction import StateSchema
from algosdk.constants import key_len_bytes


# / --- CONSTANTS
TEAL_VERSION = 7

# Descriptive field for the binding of Smart ASA App ID into the Underlying ASA url.
SMART_ASA_APP_BINDING = "smart-asa-app-id:"

# NOTE: The following costs could change over time with protocol upgrades.
OPTIN_COST = 100_000
UINTS_COST = 28_500
BYTES_COST = 50_000


def static_attrs(cls):
    return [k for k in cls.__dict__ if not k.startswith("__")]


# / --- SMART ASA ASC
# / --- --- ERRORS
class Error:
    address_length = "Invalid Address length (must be 32 bytes)"
    missing_smart_asa_id = "Smart ASA ID does not exist"
    invalid_smart_asa_id = "Invalid Smart ASA ID"
    not_creator_addr = "Caller not authorized (must be: App Creator Address)"
    not_manager_addr = "Caller not authorized (must be: Manager Address)"
    not_reserve_addr = "Caller not authorized (must be: Reserve Address)"
    not_freeze_addr = "Caller not authorized (must be: Freeze Address)"
    not_clawback_addr = "Caller not authorized (must be: Clawback Address)"
    asset_frozen = "Smart ASA is frozen"
    sender_frozen = "Sender is frozen"
    receiver_frozen = "Receiver is frozen"


# / --- --- GLOBAL STATE
class GlobalInts:
    total = Bytes("total")
    decimals = Bytes("decimals")
    default_frozen = Bytes("default_frozen")
    smart_asa_id = Bytes("smart_asa_id")
    frozen = Bytes("frozen")


class GlobalBytes:
    unit_name = Bytes("unit_name")
    name = Bytes("name")
    url = Bytes("url")
    metadata_hash = Bytes("metadata_hash")
    manager_addr = Bytes("manager_addr")
    reserve_addr = Bytes("reserve_addr")
    freeze_addr = Bytes("freeze_addr")
    clawback_addr = Bytes("clawback_addr")


class GlobalState(GlobalInts, GlobalBytes):
    @staticmethod
    def num_uints():
        return len(static_attrs(GlobalInts))

    @staticmethod
    def num_bytes():
        return len(static_attrs(GlobalBytes))

    @classmethod
    def schema(cls):
        return StateSchema(
            num_uints=cls.num_uints(),
            num_byte_slices=cls.num_bytes(),
        )


class SmartASAConfig(abi.NamedTuple):
    total: abi.Field[abi.Uint64]
    decimals: abi.Field[abi.Uint32]
    default_frozen: abi.Field[abi.Bool]
    unit_name: abi.Field[abi.String]
    name: abi.Field[abi.String]
    url: abi.Field[abi.String]
    metadata_hash: abi.Field[abi.DynamicArray[abi.Byte]]
    manager_addr: abi.Field[abi.Address]
    reserve_addr: abi.Field[abi.Address]
    freeze_addr: abi.Field[abi.Address]
    clawback_addr: abi.Field[abi.Address]


# / --- --- LOCAL STATE
# NOTE: Local State is needed only if the Smart ASA has `account_frozen`.
# Local State is not needed in case Smart ASA has just "global" `asset_freeze`.
class LocalInts:
    smart_asa_id = Bytes("smart_asa_id")
    frozen = Bytes("frozen")


class LocalBytes:
    ...


class LocalState(LocalInts, LocalBytes):
    @staticmethod
    def num_uints():
        return len(static_attrs(LocalInts))

    @staticmethod
    def num_bytes():
        return len(static_attrs(LocalBytes))

    @classmethod
    def schema(cls):
        return StateSchema(
            num_uints=cls.num_uints(),
            num_byte_slices=cls.num_bytes(),
        )


# / --- --- SUBROUTINES
@Subroutine(TealType.none)
def init_global_state() -> Expr:
    return Seq(
        App.globalPut(GlobalState.smart_asa_id, Int(0)),
        App.globalPut(GlobalState.total, Int(0)),
        App.globalPut(GlobalState.decimals, Int(0)),
        App.globalPut(GlobalState.default_frozen, Int(0)),
        # NOTE: ASA behaves excluding `unit_name` field if not declared:
        App.globalPut(GlobalState.unit_name, Bytes("")),
        # NOTE: ASA behaves excluding `name` field if not declared:
        App.globalPut(GlobalState.name, Bytes("")),
        # NOTE: ASA behaves excluding `url` field if not declared:
        App.globalPut(GlobalState.url, Bytes("")),
        # NOTE: ASA behaves excluding `metadata_hash` field if not declared:
        App.globalPut(GlobalState.metadata_hash, Bytes("")),
        App.globalPut(GlobalState.manager_addr, Global.zero_address()),
        App.globalPut(GlobalState.reserve_addr, Global.zero_address()),
        App.globalPut(GlobalState.freeze_addr, Global.zero_address()),
        App.globalPut(GlobalState.clawback_addr, Global.zero_address()),
        # Special Smart ASA fields
        App.globalPut(GlobalState.frozen, Int(0)),
    )


@Subroutine(TealType.none)
def init_local_state() -> Expr:
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    return Seq(
        App.localPut(Txn.sender(), LocalState.smart_asa_id, smart_asa_id),
        App.localPut(Txn.sender(), LocalState.frozen, Int(0)),
    )


@Subroutine(TealType.bytes)
def digit_to_ascii(i: Expr) -> Expr:
    """digit_to_ascii converts an integer < 10 to the ASCII byte that represents it"""
    return Extract(Bytes("0123456789"), i, Int(1))


@Subroutine(TealType.bytes)
def itoa(i: Expr) -> Expr:
    """itoa converts an integer to the ASCII byte string it represents."""
    return If(
        i == Int(0),
        Bytes("0"),
        Concat(
            If(i / Int(10) > Int(0), itoa(i / Int(10)), Bytes("")),
            digit_to_ascii(i % Int(10)),
        ),
    )


@Subroutine(TealType.bytes)
def strip_len_prefix(abi_encoded: Expr) -> Expr:
    return Suffix(abi_encoded, Int(abi.Uint16TypeSpec().byte_length_static()))


# / --- --- UNDERLYING ASA CONFIG
UNDERLYING_ASA_TOTAL = Int(2**64 - 1)
UNDERLYING_ASA_DECIMALS = Int(0)
UNDERLYING_ASA_DEFAULT_FROZEN = Int(1)
UNDERLYING_ASA_UNIT_NAME = Bytes("S-ASA")
UNDERLYING_ASA_NAME = Bytes("SMART-ASA")
UNDERLYING_ASA_URL = Concat(
    Bytes(SMART_ASA_APP_BINDING), itoa(Global.current_application_id())
)
UNDERLYING_ASA_METADATA_HASH = Bytes("")
UNDERLYING_ASA_MANAGER_ADDR = Global.current_application_address()
UNDERLYING_ASA_RESERVE_ADDR = Global.current_application_address()
UNDERLYING_ASA_FREEZE_ADDR = Global.current_application_address()
UNDERLYING_ASA_CLAWBACK_ADDR = Global.current_application_address()


@Subroutine(TealType.uint64)
def underlying_asa_create_inner_tx() -> Expr:
    return Seq(
        InnerTxnBuilder.Execute(
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
        Return(InnerTxn.created_asset_id()),
    )


@Subroutine(TealType.none)
def smart_asa_transfer_inner_txn(
    smart_asa_id: Expr,
    asset_amount: Expr,
    asset_sender: Expr,
    asset_receiver: Expr,
) -> Expr:
    return InnerTxnBuilder.Execute(
        {
            TxnField.fee: Int(0),
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: smart_asa_id,
            TxnField.asset_amount: asset_amount,
            TxnField.asset_sender: asset_sender,
            TxnField.asset_receiver: asset_receiver,
        }
    )


@Subroutine(TealType.none)
def smart_asa_destroy_inner_txn(smart_asa_id: Expr) -> Expr:
    return InnerTxnBuilder.Execute(
        {
            TxnField.fee: Int(0),
            TxnField.type_enum: TxnType.AssetConfig,
            TxnField.config_asset: smart_asa_id,
        }
    )


@Subroutine(TealType.none)
def is_valid_address_bytes_length(address: Expr) -> Expr:
    # WARNING: Note this check only ensures proper bytes' length on `address`,
    # but doesn't ensure that those 32 bytes are a _proper_ Algorand address.
    return Assert(Len(address) == Int(key_len_bytes), comment=Error.address_length)


@Subroutine(TealType.uint64)
def circulating_supply(asset_id: Expr):
    smart_asa_reserve = AssetHolding.balance(
        Global.current_application_address(), asset_id
    )
    return Seq(smart_asa_reserve, UNDERLYING_ASA_TOTAL - smart_asa_reserve.value())


@Subroutine(TealType.none)
def getter_preconditions(asset_id: Expr) -> Expr:
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    is_correct_smart_asa_id = smart_asa_id == asset_id
    return Seq(
        Assert(smart_asa_id, comment=Error.missing_smart_asa_id),
        Assert(is_correct_smart_asa_id, comment=Error.invalid_smart_asa_id),
    )


# / --- --- ABI
# / --- --- BARE CALLS
@Subroutine(TealType.none)
def asset_app_create() -> Expr:
    return Seq(
        # Preconditions
        # Not mandatory - Smart ASA Application self validate its state.
        Assert(
            Txn.global_num_uints() == Int(GlobalState.num_uints()),
            comment=f"Wrong State Schema - Expexted Global Ints: "
            f"{GlobalState.num_uints()}",
        ),
        Assert(
            Txn.global_num_byte_slices() == Int(GlobalState.num_bytes()),
            comment=f"Wrong State Schema - Expexted Global Bytes: "
            f"{GlobalState.num_bytes()}",
        ),
        Assert(
            Txn.local_num_uints() == Int(LocalState.num_uints()),
            comment=f"Wrong State Schema - Expexted Local Ints: "
            f"{LocalState.num_uints()}",
        ),
        Assert(
            Txn.local_num_byte_slices() == Int(LocalState.num_bytes()),
            comment=f"Wrong State Schema - Expexted Local Bytes: "
            f"{LocalState.num_bytes()}",
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
        clear_state=OnCompleteAction.call_only(Reject()),
    ),
)


# / --- --- METHODS
@smart_asa_abi.method(opt_in=CallConfig.ALL)
def asset_app_optin(
    asset: abi.Asset,
    underlying_asa_optin: abi.AssetTransferTransaction,
) -> Expr:
    """
    Smart ASA atomic opt-in to Smart ASA App and Underlying ASA.

    Args:
        asset: Underlying ASA ID (ref. App Global State: "smart_asa_id").
        underlying_asa_optin: Underlying ASA opt-in transaction.
    """
    # On OptIn the frozen status must be set to `True` if account owns any
    # units of the underlying ASA. This prevents malicious users to circumvent
    # the `default_frozen` status by clearing their Local State. Note that this
    # could be avoided by the use of Boxes once available.
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    is_correct_smart_asa_id = smart_asa_id == asset.asset_id()
    default_frozen = App.globalGet(GlobalState.default_frozen)
    freeze_account = App.localPut(Txn.sender(), LocalState.frozen, Int(1))
    account_balance = AssetHolding().balance(Txn.sender(), asset.asset_id())
    optin_to_underlying_asa = account_balance.hasValue()
    return Seq(
        # Preconditions
        Assert(smart_asa_id, comment=Error.missing_smart_asa_id),
        Assert(is_correct_smart_asa_id, comment=Error.invalid_smart_asa_id),
        Assert(
            underlying_asa_optin.get().type_enum() == TxnType.AssetTransfer,
            comment="Underlying ASA Opt-In Txn: Wrong Txn Type (Expected: Axfer)",
        ),
        Assert(
            underlying_asa_optin.get().xfer_asset() == smart_asa_id,
            comment="Underlying ASA Opt-In Txn: Wrong Asset ID (Expected: Smart ASA ID)",
        ),
        Assert(
            underlying_asa_optin.get().sender() == Txn.sender(),
            comment="Underlying ASA Opt-In Txn: Wrong Sender (Expected: App Caller)",
        ),
        Assert(
            underlying_asa_optin.get().asset_receiver() == Txn.sender(),
            comment="Underlying ASA Opt-In Txn: Wrong Asset Receiver (Expected: App Caller)",
        ),
        Assert(
            underlying_asa_optin.get().asset_amount() == Int(0),
            comment="Underlying ASA Opt-In Txn: Wrong Asset Amount (Expected: 0)",
        ),
        Assert(
            underlying_asa_optin.get().asset_close_to() == Global.zero_address(),
            comment="Underlying ASA Opt-In Txn: Wrong Asset CloseTo (Expected: Zero Address)",
        ),
        account_balance,
        Assert(optin_to_underlying_asa, comment="Missing Opt-In to Underlying ASA"),
        # Effects
        init_local_state(),
        If(Or(default_frozen, account_balance.value() > Int(0))).Then(freeze_account),
        Approve(),
    )


@smart_asa_abi.method
def asset_create(
    total: abi.Uint64,
    decimals: abi.Uint32,
    default_frozen: abi.Bool,
    unit_name: abi.String,
    name: abi.String,
    url: abi.String,
    metadata_hash: abi.DynamicArray[abi.Byte],
    manager_addr: abi.Address,
    reserve_addr: abi.Address,
    freeze_addr: abi.Address,
    clawback_addr: abi.Address,
    *,
    output: abi.Uint64,
) -> Expr:
    """
    Create a Smart ASA (triggers inner creation of an Underlying ASA).

    Args:
        total: The total number of base units of the Smart ASA to create.
        decimals: The number of digits to use after the decimal point when displaying the Smart ASA. If 0, the Smart ASA is not divisible.
        default_frozen: Smart ASA default frozen status (True to freeze holdings by default).
        unit_name: The name of a unit of Smart ASA.
        name: The name of the Smart ASA.
        url: Smart ASA external URL.
        metadata_hash: Smart ASA metadata hash (suggested 32 bytes hash).
        manager_addr: The address of the account that can manage the configuration of the Smart ASA and destroy it.
        reserve_addr: The address of the account that holds the reserve (non-minted) units of the asset and can mint or burn units of Smart ASA.
        freeze_addr: The address of the account that can freeze/unfreeze holdings of this Smart ASA globally or locally (specific accounts). If empty, freezing is not permitted.
        clawback_addr: The address of the account that can clawback holdings of this asset. If empty, clawback is not permitted.

    Returns:
        New Smart ASA ID.
    """

    is_creator = Txn.sender() == Global.creator_address()
    smart_asa_not_created = Not(App.globalGet(GlobalState.smart_asa_id))
    smart_asa_id = underlying_asa_create_inner_tx()

    return Seq(
        # Preconditions
        Assert(is_creator, comment=Error.not_creator_addr),
        Assert(smart_asa_not_created, comment="Smart ASA ID already exists"),
        is_valid_address_bytes_length(manager_addr.get()),
        is_valid_address_bytes_length(reserve_addr.get()),
        is_valid_address_bytes_length(freeze_addr.get()),
        is_valid_address_bytes_length(clawback_addr.get()),
        # Effects
        # Underlying ASA creation
        App.globalPut(GlobalState.smart_asa_id, smart_asa_id),
        # Smart ASA properties
        App.globalPut(GlobalState.total, total.get()),
        App.globalPut(GlobalState.decimals, decimals.get()),
        App.globalPut(GlobalState.default_frozen, default_frozen.get()),
        App.globalPut(GlobalState.unit_name, unit_name.get()),
        App.globalPut(GlobalState.name, name.get()),
        App.globalPut(GlobalState.url, url.get()),
        App.globalPut(
            GlobalState.metadata_hash, strip_len_prefix(metadata_hash.encode())
        ),
        App.globalPut(GlobalState.manager_addr, manager_addr.get()),
        App.globalPut(GlobalState.reserve_addr, reserve_addr.get()),
        App.globalPut(GlobalState.freeze_addr, freeze_addr.get()),
        App.globalPut(GlobalState.clawback_addr, clawback_addr.get()),
        output.set(App.globalGet(GlobalState.smart_asa_id)),
    )


@smart_asa_abi.method
def asset_config(
    config_asset: abi.Asset,
    total: abi.Uint64,
    decimals: abi.Uint32,
    default_frozen: abi.Bool,
    unit_name: abi.String,
    name: abi.String,
    url: abi.String,
    metadata_hash: abi.DynamicArray[abi.Byte],
    manager_addr: abi.Address,
    reserve_addr: abi.Address,
    freeze_addr: abi.Address,
    clawback_addr: abi.Address,
) -> Expr:
    """
    Configure the Smart ASA. Use existing values for unchanged parameters. Setting Smart ASA roles to zero-address is irreversible.

    Args:
        config_asset: Underlying ASA ID to configure (ref. App Global State: "smart_asa_id").
        total: The total number of base units of the Smart ASA to create. It can not be configured to less than its current circulating supply.
        decimals: The number of digits to use after the decimal point when displaying the Smart ASA. If 0, the Smart ASA is not divisible.
        default_frozen: Smart ASA default frozen status (True to freeze holdings by default).
        unit_name: The name of a unit of Smart ASA.
        name: The name of the Smart ASA.
        url: Smart ASA external URL.
        metadata_hash: Smart ASA metadata hash (suggested 32 bytes hash).
        manager_addr: The address of the account that can manage the configuration of the Smart ASA and destroy it.
        reserve_addr: The address of the account that holds the reserve (non-minted) units of the asset and can mint or burn units of Smart ASA.
        freeze_addr: The address of the account that can freeze/unfreeze holdings of this Smart ASA globally or locally (specific accounts). If empty, freezing is not permitted.
        clawback_addr: The address of the account that can clawback holdings of this asset. If empty, clawback is not permitted.
    """

    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    current_manager_addr = App.globalGet(GlobalState.manager_addr)
    current_reserve_addr = App.globalGet(GlobalState.reserve_addr)
    current_freeze_addr = App.globalGet(GlobalState.freeze_addr)
    current_clawback_addr = App.globalGet(GlobalState.clawback_addr)

    is_manager_addr = Txn.sender() == current_manager_addr
    is_correct_smart_asa_id = smart_asa_id == config_asset.asset_id()

    update_reserve_addr = current_reserve_addr != reserve_addr.get()
    update_freeze_addr = current_freeze_addr != freeze_addr.get()
    update_clawback_addr = current_clawback_addr != clawback_addr.get()

    # NOTE: In ref. implementation Smart ASA total can not be configured to
    # less than its current circulating supply.
    is_valid_total = total.get() >= circulating_supply(smart_asa_id)

    return Seq(
        # Preconditions
        Assert(smart_asa_id, comment=Error.missing_smart_asa_id),
        # NOTE: useless in ref. impl since 1 ASA : 1 App
        Assert(is_correct_smart_asa_id, comment=Error.invalid_smart_asa_id),
        is_valid_address_bytes_length(manager_addr.get()),
        is_valid_address_bytes_length(reserve_addr.get()),
        is_valid_address_bytes_length(freeze_addr.get()),
        is_valid_address_bytes_length(clawback_addr.get()),
        Assert(is_manager_addr, comment=Error.not_manager_addr),
        If(update_reserve_addr).Then(
            Assert(
                current_reserve_addr != Global.zero_address(),
                comment="Reserve Address has been deleted",
            )
        ),
        If(update_freeze_addr).Then(
            Assert(
                current_freeze_addr != Global.zero_address(),
                comment="Freeze Address has been deleted",
            )
        ),
        If(update_clawback_addr).Then(
            Assert(
                current_clawback_addr != Global.zero_address(),
                comment="Clawback Address has been deleted",
            )
        ),
        Assert(is_valid_total, comment="Invalid Total (must be >= Circulating Supply)"),
        # Effects
        App.globalPut(GlobalState.total, total.get()),
        App.globalPut(GlobalState.decimals, decimals.get()),
        App.globalPut(GlobalState.default_frozen, default_frozen.get()),
        App.globalPut(GlobalState.unit_name, unit_name.get()),
        App.globalPut(GlobalState.name, name.get()),
        App.globalPut(GlobalState.url, url.get()),
        App.globalPut(
            GlobalState.metadata_hash, strip_len_prefix(metadata_hash.encode())
        ),
        App.globalPut(GlobalState.manager_addr, manager_addr.get()),
        App.globalPut(GlobalState.reserve_addr, reserve_addr.get()),
        App.globalPut(GlobalState.freeze_addr, freeze_addr.get()),
        App.globalPut(GlobalState.clawback_addr, clawback_addr.get()),
    )


@smart_asa_abi.method
def asset_transfer(
    xfer_asset: abi.Asset,
    asset_amount: abi.Uint64,
    asset_sender: abi.Account,
    asset_receiver: abi.Account,
) -> Expr:
    """
    Smart ASA transfers: regular, clawback (Clawback Address), mint or burn (Reserve Address).

    Args:
        xfer_asset: Underlying ASA ID to transfer (ref. App Global State: "smart_asa_id").
        asset_amount: Smart ASA amount to transfer.
        asset_sender: Smart ASA sender, for regular transfer this must be equal to the Smart ASA App caller.
        asset_receiver: The recipient of the Smart ASA transfer.
    """
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    clawback_addr = App.globalGet(GlobalState.clawback_addr)
    is_not_clawback = And(
        Txn.sender() == asset_sender.address(),
        Txn.sender() != clawback_addr,
    )

    # NOTE: Ref. implementation grants _minting_ premission to `reserve_addr`,
    # has restriction no restriction on who is the minting _receiver_.
    # WARNING: Setting Smart ASA `reserve` to ZERO_ADDRESS switchs-off minting.
    is_minting = And(
        Txn.sender() == App.globalGet(GlobalState.reserve_addr),
        asset_sender.address() == Global.current_application_address(),
    )

    # NOTE: Ref. implementation grants _burning_ premission to `reserve_addr`,
    # has restriction both on burning _sender_ and _receiver_ to prevent
    # _clawback_ throug burning.
    # WARNING: Setting Smart ASA `reserve` to ZERO_ADDRESS switchs-off burning.
    is_burning = And(
        Txn.sender() == App.globalGet(GlobalState.reserve_addr),
        asset_sender.address() == App.globalGet(GlobalState.reserve_addr),
        asset_receiver.address() == Global.current_application_address(),
    )

    is_clawback = Txn.sender() == clawback_addr
    is_correct_smart_asa_id = smart_asa_id == xfer_asset.asset_id()

    # NOTE: Ref. implementation checks that `smart_asa_id` is correct in Local
    # State since the App could generate a new Smart ASA (if the previous one
    # has been dystroied) requiring users to opt-in again to gain a coherent
    # new `frozen` status.
    is_current_smart_asa_id = And(
        smart_asa_id == App.localGet(asset_sender.address(), LocalState.smart_asa_id),
        smart_asa_id == App.localGet(asset_receiver.address(), LocalState.smart_asa_id),
    )
    asset_frozen = App.globalGet(GlobalState.frozen)
    asset_sender_frozen = App.localGet(asset_sender.address(), LocalState.frozen)
    asset_receiver_frozen = App.localGet(asset_receiver.address(), LocalState.frozen)
    return Seq(
        # Preconditions
        Assert(smart_asa_id, comment=Error.missing_smart_asa_id),
        Assert(is_correct_smart_asa_id, comment=Error.invalid_smart_asa_id),
        is_valid_address_bytes_length(asset_sender.address()),
        is_valid_address_bytes_length(asset_receiver.address()),
        If(is_not_clawback)
        .Then(
            # Asset Regular Transfer Preconditions
            Assert(Not(asset_frozen), comment=Error.asset_frozen),
            Assert(Not(asset_sender_frozen), comment=Error.sender_frozen),
            Assert(Not(asset_receiver_frozen), comment=Error.receiver_frozen),
            Assert(is_current_smart_asa_id, comment=Error.invalid_smart_asa_id),
        )
        .ElseIf(is_minting)
        .Then(
            # Asset Minting Preconditions
            Assert(Not(asset_frozen), comment=Error.asset_frozen),
            Assert(Not(asset_receiver_frozen), comment=Error.receiver_frozen),
            Assert(
                smart_asa_id
                == App.localGet(asset_receiver.address(), LocalState.smart_asa_id),
                comment=Error.invalid_smart_asa_id,
            ),
            # NOTE: Ref. implementation prevents minting more than `total`.
            Assert(
                circulating_supply(smart_asa_id) + asset_amount.get()
                <= App.globalGet(GlobalState.total),
                comment="Over-minting (can not mint more than Total)",
            ),
        )
        .ElseIf(is_burning)
        .Then(
            # Asset Burning Preconditions
            Assert(Not(asset_frozen), comment=Error.asset_frozen),
            Assert(Not(asset_sender_frozen), comment=Error.sender_frozen),
            Assert(
                smart_asa_id
                == App.localGet(asset_sender.address(), LocalState.smart_asa_id),
                comment=Error.invalid_smart_asa_id,
            ),
        )
        .Else(
            # Asset Clawback Preconditions
            Assert(is_clawback, comment=Error.not_clawback_addr),
            # NOTE: `is_current_smart_asa_id` implicitly checks that both
            # `asset_sender` and `asset_receiver` opted-in the Smart ASA
            # App. This ensures that _mint_ and _burn_ can not be
            # executed as _clawback_, since the Smart ASA App can not
            # opt-in to itself.
            Assert(is_current_smart_asa_id, comment=Error.invalid_smart_asa_id),
        ),
        # Effects
        smart_asa_transfer_inner_txn(
            xfer_asset.asset_id(),
            asset_amount.get(),
            asset_sender.address(),
            asset_receiver.address(),
        ),
    )


@smart_asa_abi.method
def asset_freeze(freeze_asset: abi.Asset, asset_frozen: abi.Bool) -> Expr:
    """
    Smart ASA global freeze (all accounts), called by the Freeze Address.

    Args:
        freeze_asset: Underlying ASA ID to freeze/unfreeze (ref. App Global State: "smart_asa_id").
        asset_frozen: Smart ASA ID forzen status.
    """
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    is_correct_smart_asa_id = smart_asa_id == freeze_asset.asset_id()
    is_freeze_addr = Txn.sender() == App.globalGet(GlobalState.freeze_addr)
    return Seq(
        # Asset Freeze Preconditions
        Assert(
            smart_asa_id,
            comment=Error.missing_smart_asa_id,
        ),
        Assert(
            is_correct_smart_asa_id,
            comment=Error.invalid_smart_asa_id,
        ),
        Assert(
            is_freeze_addr,
            comment=Error.not_freeze_addr,
        ),
        # Effects
        App.globalPut(GlobalState.frozen, asset_frozen.get()),
    )


@smart_asa_abi.method
def account_freeze(
    freeze_asset: abi.Asset,
    freeze_account: abi.Account,
    asset_frozen: abi.Bool,
) -> Expr:
    """
    Smart ASA local freeze (account specific), called by the Freeze Address.

    Args:
        freeze_asset: Underlying ASA ID to freeze/unfreeze (ref. App Global State: "smart_asa_id").
        freeze_account: Account to freeze/unfreeze.
        asset_frozen: Smart ASA ID forzen status.
    """
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    is_correct_smart_asa_id = smart_asa_id == freeze_asset.asset_id()
    is_freeze_addr = Txn.sender() == App.globalGet(GlobalState.freeze_addr)
    return Seq(
        # Account Freeze Preconditions
        is_valid_address_bytes_length(freeze_account.address()),
        Assert(
            smart_asa_id,
            comment=Error.missing_smart_asa_id,
        ),
        Assert(
            is_correct_smart_asa_id,
            comment=Error.invalid_smart_asa_id,
        ),
        Assert(
            is_freeze_addr,
            comment=Error.not_freeze_addr,
        ),
        # Effects
        App.localPut(freeze_account.address(), LocalState.frozen, asset_frozen.get()),
    )


@smart_asa_abi.method(close_out=CallConfig.ALL)
def asset_app_closeout(
    close_asset: abi.Asset,
    close_to: abi.Account,
) -> Expr:
    """
    Smart ASA atomic close-out of Smart ASA App and Underlying ASA.

    Args:
        close_asset: Underlying ASA ID to close-out (ref. App Global State: "smart_asa_id").
        close_to: Account to send all Smart ASA reminder to. If the asset/account is forzen then this must be set to Smart ASA Creator.
    """
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    is_correct_smart_asa_id = smart_asa_id == close_asset.asset_id()
    current_smart_asa_id = App.localGet(Txn.sender(), LocalState.smart_asa_id)
    is_current_smart_asa_id = current_smart_asa_id == close_asset.asset_id()
    account_balance = AssetHolding().balance(Txn.sender(), close_asset.asset_id())
    asset_creator = AssetParam().creator(close_asset.asset_id())
    asset_frozen = App.globalGet(GlobalState.frozen)
    asset_closer_frozen = App.localGet(Txn.sender(), LocalState.frozen)
    asa_closeout_relative_idx = Txn.group_index() + Int(1)
    return Seq(
        # Preconditions
        # NOTE: Smart ASA existence is not checked by default on close-out
        # since would be impossible to close-out destroyed assets.
        is_valid_address_bytes_length(close_to.address()),
        Assert(
            is_current_smart_asa_id,
            comment=Error.invalid_smart_asa_id,
        ),
        Assert(
            Global.group_size() > asa_closeout_relative_idx,
            comment="Smart ASA CloseOut: Wrong group size (Expected: 2)",
        ),
        Assert(
            Gtxn[asa_closeout_relative_idx].type_enum() == TxnType.AssetTransfer,
            comment="Underlying ASA CloseOut Txn: Wrong Txn type (Expected: Axfer)",
        ),
        Assert(
            Gtxn[asa_closeout_relative_idx].xfer_asset() == close_asset.asset_id(),
            comment="Underlying ASA CloseOut Txn: Wrong ASA ID (Expected: Smart ASA ID)",
        ),
        Assert(
            Gtxn[asa_closeout_relative_idx].sender() == Txn.sender(),
            comment="Underlying ASA CloseOut Txn: Wrong sender (Expected: Smart ASA CloseOut caller)",
        ),
        Assert(
            Gtxn[asa_closeout_relative_idx].asset_amount() == Int(0),
            comment="Underlying ASA CloseOut Txn: Wrong amount (Expected: 0)",
        ),
        Assert(
            Gtxn[asa_closeout_relative_idx].asset_close_to()
            == Global.current_application_address(),
            comment="Underlying ASA CloseOut Txn: Wrong CloseTo address (Expected: Smart ASA App Account)",
        ),
        # Effects
        asset_creator,
        # NOTE: Skip checks if Underlying ASA has been destroyed to avoid
        # users' lock-in.
        If(asset_creator.hasValue()).Then(
            # NOTE: Smart ASA has not been destroyed.
            Assert(is_correct_smart_asa_id, comment=Error.invalid_smart_asa_id),
            If(Or(asset_frozen, asset_closer_frozen)).Then(
                # NOTE: If Smart ASA is frozen, users can only close-out to
                # Creator
                Assert(
                    close_to.address() == Global.current_application_address(),
                    comment="Wrong CloseTo address: Frozen Smart ASA must be closed-out to creator",
                ),
            ),
            If(close_to.address() != Global.current_application_address()).Then(
                # NOTE: If the target of close-out is not Creator, it MUST be
                # opted-in to the current Smart ASA.
                Assert(
                    smart_asa_id
                    == App.localGet(close_to.address(), LocalState.smart_asa_id),
                    comment=Error.invalid_smart_asa_id,
                )
            ),
            account_balance,
            smart_asa_transfer_inner_txn(
                close_asset.asset_id(),
                account_balance.value(),
                Txn.sender(),
                close_to.address(),
            ),
        ),
        # NOTE: If Smart ASA has been destroyed:
        #   1. The close-to address could be anyone
        #   2. No InnerTxn happens
        Approve(),
    )


@smart_asa_abi.method
def asset_destroy(destroy_asset: abi.Asset) -> Expr:
    """
    Destroy the Underlying ASA, must be called by Manager Address.

    Args:
        destroy_asset: Underlying ASA ID to destroy (ref. App Global State: "smart_asa_id").
    """
    smart_asa_id = App.globalGet(GlobalState.smart_asa_id)
    is_correct_smart_asa_id = smart_asa_id == destroy_asset.asset_id()
    is_manager_addr = Txn.sender() == App.globalGet(GlobalState.manager_addr)
    return Seq(
        # Asset Destroy Preconditions
        Assert(
            smart_asa_id,
            comment=Error.missing_smart_asa_id,
        ),
        Assert(
            is_correct_smart_asa_id,
            comment=Error.invalid_smart_asa_id,
        ),
        Assert(
            is_manager_addr,
            comment=Error.not_manager_addr,
        ),
        # Effects
        smart_asa_destroy_inner_txn(destroy_asset.asset_id()),
        init_global_state(),
    )


# / --- --- GETTERS
@smart_asa_abi.method
def get_asset_is_frozen(freeze_asset: abi.Asset, *, output: abi.Bool) -> Expr:
    """
    Get Smart ASA global frozen status.

    Args:
        freeze_asset: Underlying ASA ID (ref. App Global State: "smart_asa_id").

    Returns:
        Smart ASA global frozen status.
    """
    return Seq(
        # Preconditions
        getter_preconditions(freeze_asset.asset_id()),
        # Effects
        output.set(App.globalGet(GlobalState.frozen)),
    )


@smart_asa_abi.method
def get_account_is_frozen(
    freeze_asset: abi.Asset, freeze_account: abi.Account, *, output: abi.Bool
) -> Expr:
    """
    Get Smart ASA local frozen status (account specific).

    Args:
        freeze_asset: Underlying ASA ID (ref. App Global State: "smart_asa_id").
        freeze_account: Account to check.

    Returns:
        Smart ASA local frozen status (account specific).
    """
    return Seq(
        # Preconditions
        getter_preconditions(freeze_asset.asset_id()),
        is_valid_address_bytes_length(freeze_account.address()),
        # Effects
        output.set(App.localGet(freeze_account.address(), LocalState.frozen)),
    )


@smart_asa_abi.method
def get_circulating_supply(asset: abi.Asset, *, output: abi.Uint64) -> Expr:
    """
    Get Smart ASA circulating supply.

    Args:
        asset: Underlying ASA ID (ref. App Global State: "smart_asa_id").

    Returns:
        Smart ASA circulating supply.
    """
    return Seq(
        # Preconditions
        getter_preconditions(asset.asset_id()),
        # Effects
        output.set(circulating_supply(asset.asset_id())),
    )


@smart_asa_abi.method
def get_optin_min_balance(asset: abi.Asset, *, output: abi.Uint64) -> Expr:
    """
    Get Smart ASA required minimum balance (including Underlying ASA and App Local State).

    Args:
        asset: Underlying ASA ID (ref. App Global State: "smart_asa_id").

    Returns:
        Smart ASA required minimum balance in microALGO.
    """
    min_balance = Int(
        OPTIN_COST
        + UINTS_COST * LocalState.num_uints()
        + BYTES_COST * LocalState.num_bytes()
    )

    return Seq(
        # Preconditions
        getter_preconditions(asset.asset_id()),
        # Effects
        output.set(min_balance),
    )


@smart_asa_abi.method
def get_asset_config(asset: abi.Asset, *, output: SmartASAConfig) -> Expr:
    """
    Get Smart ASA configuration.

    Args:
        asset: Underlying ASA ID (ref. App Global State: "smart_asa_id").

    Returns:
        Smart ASA configuration parameters.
    """
    return Seq(
        # Preconditions
        getter_preconditions(asset.asset_id()),
        # Effects
        (total := abi.Uint64()).set(App.globalGet(GlobalState.total)),
        (decimals := abi.Uint32()).set(App.globalGet(GlobalState.decimals)),
        (default_frozen := abi.Bool()).set(App.globalGet(GlobalState.default_frozen)),
        (unit_name := abi.String()).set(App.globalGet(GlobalState.unit_name)),
        (name := abi.String()).set(App.globalGet(GlobalState.name)),
        (url := abi.String()).set(App.globalGet(GlobalState.url)),
        (metadata_hash_str := abi.String()).set(
            App.globalGet(GlobalState.metadata_hash)
        ),
        (metadata_hash := abi.make(abi.DynamicArray[abi.Byte])).decode(
            metadata_hash_str.encode()
        ),
        (manager_addr := abi.Address()).set(App.globalGet(GlobalState.manager_addr)),
        (reserve_addr := abi.Address()).set(App.globalGet(GlobalState.reserve_addr)),
        (freeze_addr := abi.Address()).set(App.globalGet(GlobalState.freeze_addr)),
        (clawback_addr := abi.Address()).set(App.globalGet(GlobalState.clawback_addr)),
        output.set(
            total,
            decimals,
            default_frozen,
            unit_name,
            name,
            url,
            metadata_hash,
            manager_addr,
            reserve_addr,
            freeze_addr,
            clawback_addr,
        ),
    )


def compile_stateful(program: Expr) -> str:
    return compileTeal(
        program,
        Mode.Application,
        version=TEAL_VERSION,
        assembleConstants=True,
        optimize=OptimizeOptions(scratch_slots=True),
    )


if __name__ == "__main__":
    # Allow quickly testing compilation.
    from smart_asa_test import test_compile

    test_compile(*smart_asa_abi.build_program())
