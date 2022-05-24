"""Smart ASA test suite"""

import json
import pprint
import pytest

from pyteal import Expr, Router

from algosdk import algod
from algosdk.abi import Contract
from algosdk.future import transaction
from algosdk.error import AlgodHTTPError

from sandbox import Sandbox
from account import Account, AppAccount

from smart_asa_asc import (
    smart_asa_abi,
    compile_stateful,
    smart_asa_local_state,
    smart_asa_global_state,
)


INITIAL_FUNDS = 10_000_000


@pytest.fixture(scope="session")
def _algod_client():
    return Sandbox.algod_client


@pytest.fixture()
def smart_asa_abi_router() -> Router:
    return smart_asa_abi


@pytest.fixture()
def pyteal_approval(smart_asa_abi_router: Router) -> Expr:
    approval, _, _ = smart_asa_abi_router.build_program()
    return approval


@pytest.fixture()
def pyteal_clear(smart_asa_abi_router: Router) -> Expr:
    _, clear, _ = smart_asa_abi_router.build_program()
    return clear


@pytest.fixture()
def teal_approval(pyteal_approval: Expr) -> str:
    return compile_stateful(pyteal_approval)


@pytest.fixture()
def teal_clear(pyteal_clear: Expr) -> str:
    return compile_stateful(pyteal_clear)


@pytest.fixture()
def smart_asa_interface(smart_asa_abi_router: Router) -> dict:
    _, _, interface = smart_asa_abi_router.build_program()
    return interface


@pytest.fixture()
def smart_asa_contract(smart_asa_interface: dict) -> Contract:
    return Contract.from_json(json.dumps(smart_asa_interface, indent=4))


@pytest.fixture()
def creator() -> Account:
    return Sandbox.create(funds_amount=INITIAL_FUNDS)


@pytest.fixture()
def eve() -> Account:
    return Sandbox.create(funds_amount=INITIAL_FUNDS)


@pytest.fixture()
def smart_asa_app(
    _algod_client: algod.AlgodClient,
    teal_approval: str,
    teal_clear: str,
    creator: Account,
) -> AppAccount:
    return creator.create_asc(
        approval_program=teal_approval,
        clear_program=teal_clear,
        global_schema=smart_asa_global_state,
        local_schema=smart_asa_local_state,
    )


def test_compile(
    pyteal_approval: Expr, pyteal_clear: Expr, smart_asa_interface: dict
) -> None:
    # This test simply ensures we can compile the ASC programs
    teal_approval_program = compile_stateful(pyteal_approval)
    teal_clear_program = compile_stateful(pyteal_clear)

    pprint.pprint("\nABI\n" + json.dumps(smart_asa_interface))

    print("\nAPPROVAL PROGRAM\n" + teal_approval_program)
    with open("/tmp/approval.teal", "w") as f:
        f.write(teal_approval_program)

    print("\nCLEAR PROGRAM\n" + teal_clear_program)
    with open("/tmp/clear.teal", "w") as f:
        f.write(teal_clear_program)


def test_smart_asa_app_create(
    _algod_client: algod.AlgodClient,
    teal_approval: str,
    teal_clear: str,
    creator: Account,
) -> None:

    # 1. Smart ASA App must be invoked with right State Schema
    with pytest.raises(AlgodHTTPError):
        print("\n --- Smart ASA App must be invoked with right State Schema.")
        creator.create_asc(
            approval_program=teal_approval,
            clear_program=teal_clear,
            global_schema=transaction.StateSchema(0, 0),
            local_schema=transaction.StateSchema(0, 0),
        )
        print(" --- Rejected as expected!")

    # Happy path
    smart_asa_app_id = creator.create_asc(
        approval_program=teal_approval,
        clear_program=teal_clear,
        global_schema=smart_asa_global_state,
        local_schema=smart_asa_local_state,
    )
    print(f"\n --- Smart ASA App ID: {smart_asa_app_id}")


class TestSmartASAMethod:
    def test_asset_create(
        self,
        eve: Account,
        creator: Account,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
    ):
        # 1. Asset Create can only be called by Smart ASA App Creator
        # Happy path
        # 2. Asset Create can not be called multiple times
        pass
