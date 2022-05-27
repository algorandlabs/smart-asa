"""
Smart ASA test suite
"""

__author__ = "Cosimo Bassi, Stefano De Angelis"
__email__ = "<cosimo.bassi@algorand.com>, <stefano.deangelis@algorand.com>"

import json
import pprint

from typing import Callable

import pytest

from pyteal import Expr, Router

from algosdk import algod
from algosdk.abi import Contract
from algosdk.error import AlgodHTTPError
from algosdk.constants import ZERO_ADDRESS
from algosdk.future import transaction

from sandbox import Sandbox
from account import Account, AppAccount

from smart_asa_asc import (
    SMART_ASA_GS,
    smart_asa_abi,
    compile_stateful,
    smart_asa_local_state,
    smart_asa_global_state,
)

from smart_asa_client import (
    smart_asa_create,
    smart_asa_config,
)

from utils import get_global_state

INITIAL_FUNDS = 10_000_000


@pytest.fixture(scope="session")
def _algod_client() -> algod.AlgodClient:
    return Sandbox.algod_client


@pytest.fixture(scope="session")
def smart_asa_abi_router() -> Router:
    return smart_asa_abi


@pytest.fixture(scope="session")
def pyteal_approval(smart_asa_abi_router: Router) -> Expr:
    approval, _, _ = smart_asa_abi_router.build_program()
    return approval


@pytest.fixture(scope="session")
def pyteal_clear(smart_asa_abi_router: Router) -> Expr:
    _, clear, _ = smart_asa_abi_router.build_program()
    return clear


@pytest.fixture(scope="session")
def teal_approval(pyteal_approval: Expr) -> str:
    return compile_stateful(pyteal_approval)


@pytest.fixture(scope="session")
def teal_clear(pyteal_clear: Expr) -> str:
    return compile_stateful(pyteal_clear)


@pytest.fixture(scope="session")
def smart_asa_contract(smart_asa_abi_router: Router) -> Contract:
    _, _, contract = smart_asa_abi_router.build_program()
    return contract


@pytest.fixture(scope="class")
def creator() -> Account:
    return Sandbox.create(funds_amount=INITIAL_FUNDS)


@pytest.fixture(scope="class")
def eve() -> Account:
    return Sandbox.create(funds_amount=INITIAL_FUNDS)


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
def opted_in_creator(
    creator: Account, smart_asa_app: AppAccount, smart_asa_id: int
) -> Account:
    creator.optin_to_asset(smart_asa_id)
    creator.optin_to_application(
        smart_asa_app.app_id,
        foreign_assets=[smart_asa_id],
    )
    return creator


@pytest.fixture(scope="function")
def opted_in_account_factory(smart_asa_app: AppAccount, smart_asa_id: int) -> Callable:
    def _factory() -> Account:
        account = Sandbox.create(funds_amount=INITIAL_FUNDS)
        account.optin_to_asset(smart_asa_id)
        account.optin_to_application(
            smart_asa_app.app_id,
            foreign_assets=[smart_asa_id],
        )
        return account

    return _factory


def test_compile(
    pyteal_approval: Expr, pyteal_clear: Expr, smart_asa_contract: Contract
) -> None:
    # This test simply ensures we can compile the ASC programs
    teal_approval_program = compile_stateful(pyteal_approval)
    teal_clear_program = compile_stateful(pyteal_clear)

    pprint.pprint("\nABI\n" + json.dumps(smart_asa_contract.dictify()))

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
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_contract: Contract,
    ) -> None:

        print("\n --- Creating Smart ASA not with App Creator...")
        with pytest.raises(AlgodHTTPError):
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
        with pytest.raises(AlgodHTTPError):
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

        smart_asa = get_global_state(_algod_client, smart_asa_app.app_id)
        assert smart_asa[SMART_ASA_GS["smart_asa_id"].byte_str[1:-1]] != 0
        assert smart_asa[SMART_ASA_GS["total"].byte_str[1:-1]] == 100


class TestAssetConfig:
    def test_smart_asa_not_created(
        self,
        _algod_client: algod.AlgodClient,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_contract: Contract,
    ) -> None:

        print("\n --- Configuring unexisting Smart ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                _algod_client=_algod_client,
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                smart_asa_id=42,
                config_manager_addr=ZERO_ADDRESS,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_is_manager(
        self,
        _algod_client: algod.AlgodClient,
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_contract: Contract,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Configuring Smart ASA not with Smart ASA Manager...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                _algod_client=_algod_client,
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=eve,
                smart_asa_id=smart_asa_id,
                config_manager_addr=ZERO_ADDRESS,
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
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                _algod_client=_algod_client,
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                smart_asa_id=42,
                config_manager_addr=ZERO_ADDRESS,
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
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            manager=creator,
            smart_asa_id=smart_asa_id,
            config_total=0,
            config_decimals=100,
            config_default_frozen=True,
            config_unit_name="NEW_TEST_!!!",
            config_asset_name="New Test !!!",
            config_url="https://new_test.io",
            config_metadata_hash="a" * 32,
            config_manager_addr=eve,
            config_reserve_addr=eve,
            config_freeze_addr=eve,
            config_clawback_addr=eve,
        )
        print(" --- Configured Smart ASA ID:", configured_smart_asa_id)

        smart_asa = get_global_state(_algod_client, smart_asa_app.app_id)
        assert smart_asa[SMART_ASA_GS["total"].byte_str[1:-1]] == 100
        assert smart_asa[SMART_ASA_GS["decimals"].byte_str[1:-1]] == 100
        assert smart_asa[SMART_ASA_GS["default_frozen"].byte_str[1:-1]] == 0
        assert smart_asa[SMART_ASA_GS["unit_name"].byte_str[1:-1]] == b"NEW_TEST_!!!"
        assert smart_asa[SMART_ASA_GS["asset_name"].byte_str[1:-1]] == b"New Test !!!"
        assert smart_asa[SMART_ASA_GS["url"].byte_str[1:-1]] == b"https://new_test.io"
        assert smart_asa[SMART_ASA_GS["metadata_hash"].byte_str[1:-1]] == b"a" * 32
        assert (
            smart_asa[SMART_ASA_GS["manager_addr"].byte_str[1:-1]]
            == eve.decoded_address
        )
        assert (
            smart_asa[SMART_ASA_GS["reserve_addr"].byte_str[1:-1]]
            == eve.decoded_address
        )
        assert (
            smart_asa[SMART_ASA_GS["freeze_addr"].byte_str[1:-1]] == eve.decoded_address
        )
        assert (
            smart_asa[SMART_ASA_GS["clawback_addr"].byte_str[1:-1]]
            == eve.decoded_address
        )


# class TestAssetTransfer:
#     def test_happy_path_minting(
#         self,
#         _algod_client: algod.AlgodClient,
#         smart_asa_contract: Contract,
#         smart_asa_app: AppAccount,
#         smart_asa_id: int,
#         opted_in_creator: Account,
#     ):
#         smart_asa_transfer(
#             _algod_client=_algod_client,
#             smart_asa_contract=smart_asa_contract,
#             smart_asa_app=smart_asa_app,
#             xfer_asset=smart_asa_id,
#             asset_amount=100,
#             caller=opted_in_creator,
#             asset_receiver=opted_in_creator,
#             asset_sender=smart_asa_app,
#         )
