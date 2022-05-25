"""Smart ASA test suite"""

import json
import pprint

import pytest

from pyteal import Expr, Router

from algosdk import algod
from algosdk.abi import Contract
from algosdk.constants import ZERO_ADDRESS
from algosdk.future import transaction

from sandbox import Sandbox
from account import Account, AppAccount

from smart_asa_asc import (
    smart_asa_abi,
    compile_stateful,
    smart_asa_local_state,
    smart_asa_global_state,
)

from smart_asa_client import (
    smart_asa_create,
    smart_asa_config,
)

INITIAL_FUNDS = 10_000_000


@pytest.fixture(scope="session")
def _algod_client() -> algod.AlgodClient:
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
    smart_asa_asc_account = creator.create_asc(
        approval_program=teal_approval,
        clear_program=teal_clear,
        global_schema=smart_asa_global_state,
        local_schema=smart_asa_local_state,
    )
    creator.pay(receiver=smart_asa_asc_account, amount=1_000_000)
    return smart_asa_asc_account


@pytest.fixture()
def smart_asa_id(
    _algod_client: algod.AlgodClient,
    smart_asa_app: AppAccount,
    creator: Account,
    smart_asa_contract: Contract,
) -> int:
    return smart_asa_create(
        _algod_client=_algod_client,
        smart_asa_app=smart_asa_app,
        creator=creator,
        smart_asa_contract=smart_asa_contract,
        total=100,
        save_abi_call="/tmp/txn.signed",
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


class TestAppCreate:
    def test_wrong_state_schema(
        self,
        teal_approval: str,
        teal_clear: str,
        creator: Account,
    ) -> None:

        with pytest.raises(Exception):
            print("\n --- Creating Smart ASA App with wrong State Schema...")
            creator.create_asc(
                approval_program=teal_approval,
                clear_program=teal_clear,
                global_schema=transaction.StateSchema(0, 0),
                local_schema=transaction.StateSchema(0, 0),
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        teal_approval: str,
        teal_clear: str,
        creator: Account,
    ) -> None:

        print("\n --- Creating Smart ASA App...")
        smart_asa_app = creator.create_asc(
            approval_program=teal_approval,
            clear_program=teal_clear,
            global_schema=smart_asa_global_state,
            local_schema=smart_asa_local_state,
        )
        print(f" --- Created Smart ASA App ID: {smart_asa_app.app_id}")


class TestAssetCreate:
    def test_is_not_creator(
        self,
        _algod_client: algod.AlgodClient,
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_contract: Contract,
    ) -> None:

        print("\n --- Creating Smart ASA not with App Creator...")
        with pytest.raises(Exception):
            smart_asa_create(
                _algod_client=_algod_client,
                smart_asa_app=smart_asa_app,
                creator=eve,
                smart_asa_contract=smart_asa_contract,
                total=100,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_smart_asa_already_created(
        self,
        _algod_client: algod.AlgodClient,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_contract: Contract,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Creating Smart ASA multiple times...")
        with pytest.raises(Exception):
            smart_asa_create(
                _algod_client=_algod_client,
                smart_asa_app=smart_asa_app,
                creator=creator,
                smart_asa_contract=smart_asa_contract,
                total=100,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        _algod_client: algod.AlgodClient,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_contract: Contract,
    ) -> None:

        print("\n --- Creating Smart ASA...")
        smart_asa_id = smart_asa_create(
            _algod_client=_algod_client,
            smart_asa_app=smart_asa_app,
            creator=creator,
            smart_asa_contract=smart_asa_contract,
            total=100,
        )
        print(" --- Created Smart ASA ID:", smart_asa_id)


class TestAssetConfig:
    def test_is_creator(
        self,
        _algod_client: algod.AlgodClient,
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_contract: Contract,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Configuring Smart ASA not with App Creator...")
        with pytest.raises(Exception):
            smart_asa_config(
                _algod_client=_algod_client,
                smart_asa_app=smart_asa_app,
                creator=eve,
                smart_asa_contract=smart_asa_contract,
                manager_addr=ZERO_ADDRESS,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_is_correct_smart_asa(
        self,
        _algod_client: algod.AlgodClient,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_contract: Contract,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Configuring Smart ASA with wrong Asset ID...")
        with pytest.raises(Exception):
            smart_asa_config(
                _algod_client=_algod_client,
                smart_asa_app=smart_asa_app,
                creator=creator,
                smart_asa_contract=smart_asa_contract,
                manager_addr=ZERO_ADDRESS,
                smart_asa_id=42,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        _algod_client: algod.AlgodClient,
        creator: Account,
        eve: Account,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Configuring Smart ASA...")
        configured_smart_asa_id = smart_asa_config(
            _algod_client=_algod_client,
            smart_asa_app=smart_asa_app,
            creator=creator,
            smart_asa_contract=smart_asa_contract,
            total=0,
            decimals=100,
            default_frozen=True,
            unit_name="NEW_TEST_!!!",
            asset_name="New Test !!!",
            url="https://new_test.io",
            metadata_hash="a" * 32,
            manager_addr=eve,
            reserve_addr=eve,
            freeze_addr=eve,
            clawback_addr=eve,
        )
        print(" --- Configured Smart ASA ID:", configured_smart_asa_id)
