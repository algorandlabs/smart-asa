"""Smart ASA test suite"""

import json
import pprint

import pytest

from pyteal import Expr, Router

from algosdk import algod
from algosdk.abi import Contract
from algosdk.constants import ZERO_ADDRESS
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction

from sandbox import Sandbox
from account import Account, AppAccount

from smart_asa_asc import (
    smart_asa_abi,
    compile_stateful,
    smart_asa_local_state,
    smart_asa_global_state,
)

from utils import (
    get_method,
    get_params,
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
    smart_asa_contract: Contract,
    creator: Account,
) -> int:

    params = get_params(_algod_client)
    abi_call_fee = params.fee * 2
    return creator.abi_call(
        get_method(smart_asa_contract, "asset_create"),
        100,
        2,
        False,
        "TEST",
        "Test Smart ASA",
        "https://test",
        "spam",
        creator.address,
        creator.address,
        creator.address,
        creator.address,
        app=smart_asa_app,
        fee=abi_call_fee,
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

        with pytest.raises(AlgodHTTPError):
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
        eve: Account,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
    ) -> None:

        params = get_params(_algod_client)
        abi_call_fee = params.fee * 2

        print("\n --- Creating Smart ASA not with App Creator...")
        with pytest.raises(Exception):
            eve.abi_call(
                get_method(smart_asa_contract, "asset_create"),
                100,
                2,
                False,
                "TEST",
                "Test Smart ASA",
                "https://test",
                "spam",
                eve.address,
                eve.address,
                eve.address,
                eve.address,
                app=smart_asa_app,
                fee=abi_call_fee,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_smart_asa_already_created(
        self,
        _algod_client: algod.AlgodClient,
        creator: Account,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
    ) -> None:

        params = get_params(_algod_client)
        abi_call_fee = params.fee * 2

        print("\n --- Creating Smart ASA multiple times...")
        with pytest.raises(Exception):
            creator.abi_call(
                get_method(smart_asa_contract, "asset_create"),
                100,
                2,
                False,
                "TEST",
                "Test Smart ASA",
                "https://test",
                "spam",
                creator.address,
                creator.address,
                creator.address,
                creator.address,
                app=smart_asa_app,
                fee=abi_call_fee,
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        _algod_client: algod.AlgodClient,
        creator: Account,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
    ) -> None:

        params = get_params(_algod_client)
        abi_call_fee = params.fee * 2

        print("\n --- Creating Smart ASA...")
        smart_asa_id = creator.abi_call(
            get_method(smart_asa_contract, "asset_create"),
            100,
            2,
            False,
            "TEST",
            "Test Smart ASA",
            "https://test",
            "spam",
            creator.address,
            creator.address,
            creator.address,
            creator.address,
            app=smart_asa_app,
            fee=abi_call_fee,
        )
        print(" --- Created Smart ASA ID:", smart_asa_id)


class TestAssetConfig:
    def test_is_creator(
        self,
        _algod_client: algod.AlgodClient,
        eve: Account,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
    ) -> None:

        params = get_params(_algod_client)
        abi_call_fee = params.fee

        print("\n --- Configuring Smart ASA not with App Creator...")
        with pytest.raises(Exception):
            eve.abi_call(
                get_method(smart_asa_contract, "asset_config"),
                smart_asa_id,
                1000,
                10,
                True,
                "NEW TEST",
                "New Test Smart ASA",
                "https://new_test",
                "new_spam",
                ZERO_ADDRESS,
                ZERO_ADDRESS,
                ZERO_ADDRESS,
                ZERO_ADDRESS,
                app=smart_asa_app,
                fee=abi_call_fee,
            )
        print(" --- Rejected as expected!")

    def test_is_correct_smart_asa(
        self,
        _algod_client: algod.AlgodClient,
        creator: Account,
        eve: Account,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
    ) -> None:

        params = get_params(_algod_client)
        abi_call_fee = params.fee

        print("\n --- Configuring Smart ASA with wrong Asset ID...")
        with pytest.raises(Exception):
            creator.abi_call(
                get_method(smart_asa_contract, "asset_config"),
                42,
                1000,
                10,
                True,
                "NEW TEST",
                "New Test Smart ASA",
                "https://new_test",
                "new_spam",
                ZERO_ADDRESS,
                ZERO_ADDRESS,
                ZERO_ADDRESS,
                ZERO_ADDRESS,
                app=smart_asa_app,
                fee=abi_call_fee,
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

        params = get_params(_algod_client)
        abi_call_fee = params.fee

        print("\n --- Configuring Smart ASA...")
        creator.abi_call(
            get_method(smart_asa_contract, "asset_config"),
            smart_asa_id,
            1000,
            10,
            True,
            "NEW TEST",
            "New Test Smart ASA",
            "https://new_test",
            "new_spam",
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            app=smart_asa_app,
            fee=abi_call_fee,
        )
        print(" --- Configured Smart ASA ID:", smart_asa_id)
