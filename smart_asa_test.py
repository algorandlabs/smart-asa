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

from algosdk.abi import Contract
from algosdk.error import AlgodHTTPError
from algosdk.constants import ZERO_ADDRESS
from algosdk.future import transaction

from sandbox import Sandbox
from account import Account, AppAccount

from smart_asa_asc import (
    smart_asa_abi,
    compile_stateful,
)

from smart_asa_client import (
    get_smart_asa_params,
    smart_asa_app_create,
    smart_asa_create,
    smart_asa_config,
    smart_asa_optin,
    smart_asa_transfer,
    smart_asa_freeze,
    smart_asa_account_freeze,
    smart_asa_destroy,
    smart_asa_get,
    smart_asa_get_asset_frozen,
)

from utils import (
    get_global_state,
    get_local_state,
)

INITIAL_FUNDS = 100_000_000


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
    teal_approval: str,
    teal_clear: str,
    creator: Account,
) -> AppAccount:
    app_account = smart_asa_app_create(
        teal_approval=teal_approval,
        teal_clear=teal_clear,
        creator=creator,
    )
    creator.pay(receiver=app_account, amount=1_000_000)
    return app_account


@pytest.fixture(
    scope="function",
    params=[False, True],
    ids=["Not Frozen Smart ASA", "Default Frozen Smart ASA"],
)
def smart_asa_id(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    creator: Account,
    request,
) -> int:
    return smart_asa_create(
        smart_asa_app=smart_asa_app,
        creator=creator,
        smart_asa_contract=smart_asa_contract,
        total=100,
        default_frozen=request.param,
    )


@pytest.fixture(scope="function")
def opted_in_creator(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    creator: Account,
    smart_asa_id: int,
) -> Account:
    creator.optin_to_asset(smart_asa_id)
    smart_asa_optin(
        smart_asa_contract=smart_asa_contract,
        smart_asa_app=smart_asa_app,
        asset_id=smart_asa_id,
        caller=creator,
    )
    return creator


@pytest.fixture(scope="function")
def creator_with_supply(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    opted_in_creator: Account,
    smart_asa_id: int,
) -> Account:
    smart_asa_transfer(
        smart_asa_contract=smart_asa_contract,
        smart_asa_app=smart_asa_app,
        xfer_asset=smart_asa_id,
        asset_amount=50,
        caller=opted_in_creator,
        asset_receiver=opted_in_creator,
        asset_sender=smart_asa_app,
    )
    return opted_in_creator


@pytest.fixture(scope="function")
def opted_in_account_factory(
    smart_asa_contract: Contract, smart_asa_app: AppAccount, smart_asa_id: int
) -> Callable:
    def _factory() -> Account:
        account = Sandbox.create(funds_amount=INITIAL_FUNDS)
        account.optin_to_asset(smart_asa_id)
        smart_asa_optin(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            asset_id=smart_asa_id,
            caller=account,
        )
        return account

    return _factory


@pytest.fixture(scope="function")
def account_with_supply_factory(
    smart_asa_contract: Contract,
    smart_asa_app: AppAccount,
    smart_asa_id: int,
    creator_with_supply: Account,
    opted_in_account_factory: Callable,
) -> Callable:
    def _factory() -> Account:
        account = opted_in_account_factory()
        smart_asa_transfer(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            xfer_asset=smart_asa_id,
            asset_amount=10,
            caller=creator_with_supply,
            asset_receiver=account,
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
        smart_asa_app = smart_asa_app_create(
            teal_approval=teal_approval,
            teal_clear=teal_clear,
            creator=creator,
        )
        print(f" --- Created Smart ASA App ID: {smart_asa_app.app_id}")


class TestAssetCreate:
    def test_is_not_creator(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        eve: Account,
    ) -> None:

        print("\n --- Creating Smart ASA not with App Creator...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_create(
                smart_asa_app=smart_asa_app,
                creator=eve,
                smart_asa_contract=smart_asa_contract,
                total=100,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_smart_asa_already_created(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Creating Smart ASA multiple times...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_create(
                smart_asa_app=smart_asa_app,
                creator=creator,
                smart_asa_contract=smart_asa_contract,
                total=100,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
    ) -> None:
        print("\n --- Creating Smart ASA...")
        smart_asa_id = smart_asa_create(
            smart_asa_app=smart_asa_app,
            creator=creator,
            smart_asa_contract=smart_asa_contract,
            total=100,
        )
        print(" --- Created Smart ASA ID:", smart_asa_id)

        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["smart_asa_id"] == smart_asa_id
        assert smart_asa["total"] == 100


class TestAssetOptin:
    def test_smart_asa_not_created(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
    ) -> None:
        print("\n --- Opt-In App with no Smart ASA ID...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_optin(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                asset_id=1,
                caller=creator,
            )
        print(" --- Rejected as expected!")

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_wrong_smart_asa_id(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:
        creator.optin_to_asset(smart_asa_id)
        print("\n --- Opt-In App with wrong Smart ASA ID...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_optin(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                asset_id=smart_asa_id + 1,
                caller=creator,
            )
        print(" --- Rejected as expected!")

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_no_optin_to_underlying_asa(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Opt-In App without optin to underlying ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_optin(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                asset_id=smart_asa_id,
                caller=creator,
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        smart_asa_app: AppAccount,
        opted_in_creator: Account,
    ) -> None:
        smart_asa = get_global_state(
            algod_client=opted_in_creator.algod_client,
            asc_idx=smart_asa_app.app_id,
        )
        local_state = get_local_state(
            algod_client=opted_in_creator.algod_client,
            account_address=opted_in_creator.address,
            asc_idx=smart_asa_app.app_id,
        )
        if smart_asa["default_frozen"]:
            assert local_state["frozen"]
        else:
            assert not local_state["frozen"]


class TestAssetConfig:
    def test_smart_asa_not_created(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
    ) -> None:

        print("\n --- Configuring unexisting Smart ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                asset_id=42,
                config_manager_addr=ZERO_ADDRESS,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_is_not_manager(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_id: int,
    ) -> None:
        # NOTE: This test ensures also that once `manager_add` is set to
        # ZERO_ADDR the Smart ASA can no longer be configured.
        print("\n --- Configuring Smart ASA not with Smart ASA Manager...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=eve,
                asset_id=smart_asa_id,
                config_manager_addr=ZERO_ADDRESS,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_is_not_correct_smart_asa(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Configuring Smart ASA with wrong Asset ID...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                asset_id=42,
                config_manager_addr=ZERO_ADDRESS,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_disabled_frozen_and_clawback(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:
        print("\n --- Disabling Smart ASA Freeze and Clawback Addresses...")
        configured_smart_asa_id = smart_asa_config(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            manager=creator,
            asset_id=smart_asa_id,
            config_freeze_addr=ZERO_ADDRESS,
            config_clawback_addr=ZERO_ADDRESS,
        )
        print(" --- Configured Smart ASA ID:", configured_smart_asa_id)

        print("\n --- Changing Smart ASA Freeze Address...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                asset_id=smart_asa_id,
                config_freeze_addr=creator,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

        print("\n --- Changing Smart ASA Clawback Address...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_config(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                asset_id=smart_asa_id,
                config_clawback_addr=creator,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        eve: Account,
        smart_asa_id: int,
    ) -> None:

        config_s_asa = {
            "smart_asa_id": smart_asa_id,
            "app_id": smart_asa_app.app_id,
            "creator_addr": creator.address,
            "unit_name": "NEW_TEST_!!!",
            "name": "New Test !!!",
            "url": "https://new_test.io",
            "metadata_hash": "a" * 32,
            "total": 0,
            "decimals": 100,
            "frozen": False,
            "default_frozen": True,
            "manager_addr": eve.address,
            "reserve_addr": eve.address,
            "freeze_addr": eve.address,
            "clawback_addr": eve.address,
        }

        print("\n --- Configuring Smart ASA...")
        configured_smart_asa_id = smart_asa_config(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            manager=creator,
            asset_id=smart_asa_id,
            config_total=config_s_asa["total"],
            config_decimals=config_s_asa["decimals"],
            config_default_frozen=config_s_asa["default_frozen"],
            config_unit_name=config_s_asa["unit_name"],
            config_asset_name=config_s_asa["name"],
            config_url=config_s_asa["url"],
            config_metadata_hash=config_s_asa["metadata_hash"],
            config_manager_addr=config_s_asa["manager_addr"],
            config_reserve_addr=config_s_asa["reserve_addr"],
            config_freeze_addr=config_s_asa["freeze_addr"],
            config_clawback_addr=config_s_asa["clawback_addr"],
        )
        print(" --- Configured Smart ASA ID:", configured_smart_asa_id)

        # FIXME
        # smart_asa = get_global_state(creator.algod_client, smart_asa_app.app_id)
        # for k in smart_asa.keys():
        #     if k == 'total' or k == 'default_frozen':
        #         assert smart_asa[k] != config_s_asa[k]
        #     elif smart_asa[k] is bytes and smart_asa[k][-5:] == '_addr':
        #         assert encode_address(smart_asa[k]) == config_s_asa[k]
        #     elif smart_asa[k] is bytes:
        #         assert smart_asa[k].decode() == config_s_asa[k]
        #     else:
        #         assert smart_asa[k] == config_s_asa[k]


class TestAssetTransfer:
    def test_smart_asa_not_created(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
    ) -> None:

        print("\n --- Transferring unexisting Smart ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_transfer(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                xfer_asset=42,
                asset_amount=100,
                caller=creator,
                asset_receiver=creator,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_is_not_correct_smart_asa(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Transferring Smart ASA with wrong Asset ID...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_transfer(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                xfer_asset=42,
                asset_amount=100,
                caller=creator,
                asset_receiver=creator,
                save_abi_call="/tmp/txn.signed",
            )
        print(" --- Rejected as expected!")

    def test_happy_path_minting(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        opted_in_creator: Account,
        smart_asa_id: int,
    ) -> None:
        print(
            "\n --- Pre Minting Smart ASA Reserve:",
            smart_asa_app.asa_balance(smart_asa_id),
        )
        print("\n --- Minting Smart ASA...")
        smart_asa_transfer(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            xfer_asset=smart_asa_id,
            asset_amount=100,
            caller=opted_in_creator,
            asset_receiver=opted_in_creator,
            asset_sender=smart_asa_app,
        )
        print(
            "\n --- Post Minting Smart ASA Reserve:",
            smart_asa_app.asa_balance(smart_asa_id),
        )
        assert opted_in_creator.asa_balance(smart_asa_id) == 100

    def test_receiver_not_optedin_to_app(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator_with_supply: Account,
        eve: Account,
        smart_asa_id: int,
    ) -> None:
        eve.optin_to_asset(smart_asa_id)
        print("\n --- Transferring Smart ASA to not opted-in receiver...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_transfer(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                xfer_asset=smart_asa_id,
                asset_amount=100,
                caller=creator_with_supply,
                asset_receiver=eve,
                asset_sender=creator_with_supply,
            )
        print(" --- Rejected as expected!")

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_happy_path_transfer(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        account_with_supply_factory: Callable,
        smart_asa_id: int,
    ) -> None:
        sender = account_with_supply_factory()
        receiver = account_with_supply_factory()
        sender_balance = sender.asa_balance(smart_asa_id)
        receiver_balance = receiver.asa_balance(smart_asa_id)
        amount = 1
        print("\n --- Sender Balance Pre Transfering:", sender_balance)
        print("\n --- Receiver Balance Pre Transfering:", receiver_balance)
        print("\n --- Transferring Smart ASA...")
        smart_asa_transfer(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            xfer_asset=smart_asa_id,
            asset_amount=amount,
            caller=sender,
            asset_receiver=receiver,
        )
        print(
            "\n --- Sender Balance Post Transfering:", sender.asa_balance(smart_asa_id)
        )
        print(
            "\n --- Receiver Balance Post Transfering:",
            receiver.asa_balance(smart_asa_id),
        )
        assert sender.asa_balance(smart_asa_id) == sender_balance - amount
        assert receiver.asa_balance(smart_asa_id) == receiver_balance + amount

    def test_clawback_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        account_with_supply_factory: Callable,
        smart_asa_id: int,
    ) -> None:
        # NOTE: here we need a `clawback_addr` different from App `creator`
        # otherwise the test falls in `minting` case.
        clawback = account_with_supply_factory()
        revoke_from = account_with_supply_factory()
        receiver = account_with_supply_factory()

        print("\n --- Configuring Smart ASA...")
        smart_asa_config(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            manager=creator,
            asset_id=smart_asa_id,
            config_clawback_addr=clawback,
        )

        print("\n --- Clawbacking Smart ASA...")
        smart_asa_transfer(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            xfer_asset=smart_asa_id,
            asset_amount=1,
            caller=clawback,
            asset_sender=revoke_from,
            asset_receiver=receiver,
        )

    def test_wrong_clawback(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        account_with_supply_factory: Callable,
        smart_asa_id: int,
    ) -> None:
        clawback = account_with_supply_factory()
        revoke_from = account_with_supply_factory()
        receiver = account_with_supply_factory()

        with pytest.raises(AlgodHTTPError):
            print("\n --- Clawbacking Smart ASA with wrong clawback...")
            smart_asa_transfer(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                xfer_asset=smart_asa_id,
                asset_amount=1,
                caller=clawback,
                asset_sender=revoke_from,
                asset_receiver=receiver,
            )
        print(" --- Rejected as expected!")

    def test_self_clawback_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator_with_supply: Account,
        smart_asa_id: int,
    ) -> None:
        print("\n --- Self-Clawbacking Smart ASA...")
        smart_asa_transfer(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            xfer_asset=smart_asa_id,
            asset_amount=1,
            caller=creator_with_supply,
            asset_receiver=creator_with_supply,
        )

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_fail_if_receiver_is_frozen(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
        creator: Account,
        opted_in_account_factory: Callable,
    ) -> None:
        account = opted_in_account_factory()
        account_state = get_local_state(
            account.algod_client, account.address, smart_asa_app.app_id
        )
        assert not account_state["frozen"]
        print("\n --- Freezeing Smart ASA account...")
        smart_asa_account_freeze(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            freezer=creator,
            freeze_asset=smart_asa_id,
            target_account=account,
            account_frozen=True,
        )
        account_state = get_local_state(
            account.algod_client, account.address, smart_asa_app.app_id
        )
        assert account_state["frozen"]

        amount = 1
        print("\n --- Transferring Smart ASA to freezed account...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_transfer(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                xfer_asset=smart_asa_id,
                asset_amount=amount,
                caller=creator,
                asset_receiver=account,
            )
        print(" --- Rejected as expected!")

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_fail_if_sender_is_frozen(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
        creator: Account,
        account_with_supply_factory: Callable,
    ) -> None:
        sender = account_with_supply_factory()
        receiver = account_with_supply_factory()
        sender_state = get_local_state(
            sender.algod_client, sender.address, smart_asa_app.app_id
        )
        assert not sender_state["frozen"]
        print("\n --- Freezeing Smart ASA sender account...")
        smart_asa_account_freeze(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            freezer=creator,
            freeze_asset=smart_asa_id,
            target_account=sender,
            account_frozen=True,
        )
        account_state = get_local_state(
            sender.algod_client, sender.address, smart_asa_app.app_id
        )
        assert account_state["frozen"]

        amount = 1
        print("\n --- Transferring Smart ASA from freezed account...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_transfer(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                xfer_asset=smart_asa_id,
                asset_amount=amount,
                caller=sender,
                asset_receiver=receiver,
            )
        print(" --- Rejected as expected!")

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_fail_if_smart_asa_is_frozen(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
        creator: Account,
        account_with_supply_factory: Callable,
    ) -> None:
        sender = account_with_supply_factory()
        receiver = account_with_supply_factory()
        sender_state = get_local_state(
            sender.algod_client, sender.address, smart_asa_app.app_id
        )
        receiver_state = get_local_state(
            receiver.algod_client, receiver.address, smart_asa_app.app_id
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert not sender_state["frozen"]
        assert not receiver_state["frozen"]
        assert not smart_asa["frozen"]

        print("\n --- Freezing whole Smart ASA...")
        smart_asa_freeze(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            freezer=creator,
            freeze_asset=smart_asa_id,
            asset_frozen=True,
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["frozen"]

        amount = 1
        print("\n --- Transferring frozen Smart ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_transfer(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                xfer_asset=smart_asa_id,
                asset_amount=amount,
                caller=sender,
                asset_receiver=receiver,
            )
        print(" --- Rejected as expected!")

    # @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    # def test_fail_if_not_current_smart_asa_id(
    #     self,
    #     smart_asa_contract: Contract,
    #     smart_asa_app: AppAccount,
    #     smart_asa_id: int,
    #     opted_in_creator: Account,
    #     opted_in_account_factory: Callable
    # ) -> None:

    #     creator_state = get_local_state(
    #         opted_in_creator.algod_client, opted_in_creator.address, smart_asa_app.app_id
    #     )

    #     old_creator_smart_asa_id = creator_state['smart_asa_id']

    #     print(f"\n --- Destroying Smart ASA in App {smart_asa_app.app_id}...")
    #     smart_asa_destroy(
    #         smart_asa_contract=smart_asa_contract,
    #         smart_asa_app=smart_asa_app,
    #         manager=opted_in_creator,
    #         destroy_asset=smart_asa_id,
    #     )
    #     print(" --- Destroyed Smart ASA ID:", smart_asa_id)

    #     print(f"\n --- Creating new underlying Smart ASA in App {smart_asa_app.app_id}...")
    #     new_smart_asa_id = smart_asa_create(
    #         smart_asa_contract=smart_asa_contract,
    #         smart_asa_app=smart_asa_app,
    #         creator=opted_in_creator,
    #         total=100
    #     )

    #     print(f"\n --- Creator optin to new ASA {new_smart_asa_id}...")
    #     opted_in_creator.optin_to_asset(new_smart_asa_id)

    # TODO: To enable new optin we need the creator's `asset_close_to`

    #     print(f"\n --- Creator optin to Smart ASA App {new_smart_asa_id}...")
    #     smart_asa_optin(
    #         smart_asa_contract=smart_asa_contract,
    #         smart_asa_app=smart_asa_app,
    #         asset_id=new_smart_asa_id,
    #         caller=opted_in_creator
    #     )

    #     creator_state = get_local_state(
    #         opted_in_creator.algod_client, opted_in_creator.address, smart_asa_app.app_id
    #     )
    #     new_creator_smart_asa_id = creator_state['smart_asa_id']
    #     assert old_creator_smart_asa_id != new_creator_smart_asa_id

    #     print(
    #         "\n --- Pre Minting Smart ASA Reserve:",
    #         smart_asa_app.asa_balance(new_smart_asa_id),
    #     )
    #     print("\n --- Minting Smart ASA...")
    #     smart_asa_transfer(
    #         smart_asa_contract=smart_asa_contract,
    #         smart_asa_app=smart_asa_app,
    #         xfer_asset=new_smart_asa_id,
    #         asset_amount=100,
    #         caller=opted_in_creator,
    #         asset_receiver=opted_in_creator,
    #         asset_sender=smart_asa_app,
    #     )
    #     print(
    #         "\n --- Post Minting Smart ASA Reserve:",
    #         smart_asa_app.asa_balance(new_smart_asa_id),
    #     )
    #     assert opted_in_creator.asa_balance(new_smart_asa_id) == 100

    #     receiver = opted_in_account_factory()
    #     print(f"\n --- Receiver optin to new ASA {new_smart_asa_id}...")
    #     receiver.optin_to_asset(new_smart_asa_id)

    #     amount = 1
    #     print("\n --- Clawbacking new Smart ASA to unauthorized receiver...")
    #     with pytest.raises(AlgodHTTPError):
    #         smart_asa_transfer(
    #             smart_asa_contract=smart_asa_contract,
    #             smart_asa_app=smart_asa_app,
    #             xfer_asset=new_smart_asa_id,
    #             asset_amount=amount,
    #             caller=opted_in_creator,
    #             asset_receiver=receiver,
    #         )
    #     print(" --- Rejected as expected!")

    #     print("\n --- Removing clawback from Smart ASA ...")
    #     smart_asa_config(
    #         smart_asa_contract=smart_asa_contract,
    #         smart_asa_app=smart_asa_app,
    #         manager=opted_in_creator,
    #         asset_id=new_smart_asa_id,
    #         config_clawback_addr=ZERO_ADDRESS
    #     )

    #     print("\n --- Transferring new Smart ASA to unauthorized receiver...")
    #     with pytest.raises(AlgodHTTPError):
    #         smart_asa_transfer(
    #             smart_asa_contract=smart_asa_contract,
    #             smart_asa_app=smart_asa_app,
    #             xfer_asset=new_smart_asa_id,
    #             asset_amount=amount,
    #             caller=opted_in_creator,
    #             asset_receiver=receiver,
    #         )
    #     print(" --- Rejected as expected!")


class TestAssetFreeze:
    def test_smart_asa_not_created(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
    ) -> None:

        print("\n --- Freezing unexisting Smart ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_freeze(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                freezer=creator,
                freeze_asset=42,
                asset_frozen=True,
            )
        print(" --- Rejected as expected!")

    def test_is_not_correct_smart_asa(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Freezing Smart ASA with wrong Asset ID...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_freeze(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                freezer=creator,
                freeze_asset=42,
                asset_frozen=True,
            )
        print(" --- Rejected as expected!")

    def test_is_not_freezer(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_id: int,
    ) -> None:
        with pytest.raises(AlgodHTTPError):
            print("\n --- Unfreezeing whole Smart ASA with wrong account...")
            smart_asa_freeze(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                freezer=eve,
                freeze_asset=smart_asa_id,
                asset_frozen=False,
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert not smart_asa["frozen"]

        print("\n --- Freezeing whole Smart ASA...")
        smart_asa_freeze(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            freezer=creator,
            freeze_asset=smart_asa_id,
            asset_frozen=True,
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["frozen"]

        print("\n --- Unfreezeing whole Smart ASA...")
        smart_asa_freeze(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            freezer=creator,
            freeze_asset=smart_asa_id,
            asset_frozen=False,
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert not smart_asa["frozen"]


class TestAccountFreeze:
    def test_smart_asa_not_created(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        opted_in_account_factory: Callable,
    ) -> None:

        print("\n --- Freezing account for unexisting Smart ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_account_freeze(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                freezer=creator,
                freeze_asset=42,
                target_account=opted_in_account_factory(),
                account_frozen=True,
            )
        print(" --- Rejected as expected!")

    def test_is_not_correct_smart_asa(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
        opted_in_account_factory: Callable,
    ) -> None:

        print("\n --- Freezing account with wrong Smart ASA ID...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_account_freeze(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                freezer=creator,
                freeze_asset=42,
                target_account=opted_in_account_factory(),
                account_frozen=True,
            )
        print(" --- Rejected as expected!")

    def test_is_not_freezer(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_id: int,
    ) -> None:
        with pytest.raises(AlgodHTTPError):
            print("\n --- Unfreezeing account with wrong account...")
            smart_asa_account_freeze(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                freezer=eve,
                freeze_asset=42,
                target_account=eve,
                account_frozen=False,
            )
        print(" --- Rejected as expected!")

    @pytest.mark.parametrize("smart_asa_id", [False], indirect=True)
    def test_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
        opted_in_account_factory: Callable,
    ) -> None:
        account = opted_in_account_factory()
        account_state = get_local_state(
            account.algod_client, account.address, smart_asa_app.app_id
        )
        assert not account_state["frozen"]
        print("\n --- Freezeing Smart ASA account...")
        smart_asa_account_freeze(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            freezer=creator,
            freeze_asset=smart_asa_id,
            target_account=account,
            account_frozen=True,
        )
        account_state = get_local_state(
            account.algod_client, account.address, smart_asa_app.app_id
        )
        assert account_state["frozen"]

        print("\n --- Unfreezeing Smart ASA account...")
        smart_asa_account_freeze(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            freezer=creator,
            freeze_asset=smart_asa_id,
            target_account=account,
            account_frozen=False,
        )
        account_state = get_local_state(
            account.algod_client, account.address, smart_asa_app.app_id
        )
        assert not account_state["frozen"]


class TestAssetDestroy:
    def test_smart_asa_not_created(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
    ) -> None:

        print("\n --- Destroying unexisting Smart ASA...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_destroy(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                destroy_asset=42,
            )
        print(" --- Rejected as expected!")

    def test_is_not_correct_smart_asa(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:

        print("\n --- Destroying wrong Smart ASA ID...")
        with pytest.raises(AlgodHTTPError):
            smart_asa_destroy(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator,
                destroy_asset=42,
            )
        print(" --- Rejected as expected!")

    def test_is_not_manager(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        eve: Account,
        smart_asa_id: int,
    ) -> None:
        with pytest.raises(AlgodHTTPError):
            print("\n --- Destroying Smart ASA with wrong account...")
            smart_asa_destroy(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=eve,
                destroy_asset=smart_asa_id,
            )
        print(" --- Rejected as expected!")

    def test_smart_asa_still_in_circulation(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator_with_supply: Account,
        smart_asa_id: int,
    ) -> None:
        with pytest.raises(AlgodHTTPError):
            print(
                f"\n --- Destroying circulating Smart ASA in App"
                f" {smart_asa_app.app_id}..."
            )
            smart_asa_destroy(
                smart_asa_contract=smart_asa_contract,
                smart_asa_app=smart_asa_app,
                manager=creator_with_supply,
                destroy_asset=smart_asa_id,
            )
        print(" --- Rejected as expected!")

    def test_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        creator: Account,
        smart_asa_id: int,
    ) -> None:
        print(f"\n --- Destroying Smart ASA in App {smart_asa_app.app_id}...")
        smart_asa_destroy(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            manager=creator,
            destroy_asset=smart_asa_id,
        )
        print(" --- Destroyed Smart ASA ID:", smart_asa_id)


# FIXME: Restore tests once `asset_close_to` is fixed.
# class TestAssetCloseout:
#     def test_happy_path(
#         self,
#         smart_asa_contract: Contract,
#         smart_asa_app: AppAccount,
#         smart_asa_id: int,
#         opted_in_creator: Account,
#     ) -> None:
#         print(f"\n --- Closing out Smart ASA in App {smart_asa_app.app_id}...")
#         smart_asa_closeout(
#             smart_asa_contract=smart_asa_contract,
#             smart_asa_app=smart_asa_app,
#             asset_id=smart_asa_id,
#             closer=opted_in_creator,
#         )
#         print(" --- Closed out Smart ASA ID:", smart_asa_id)
#         closer_state = get_local_state(
#             opted_in_creator.algod_client,
#             opted_in_creator.address,
#             smart_asa_app.app_id,
#         )
#         print(closer_state)


class TestGetters:
    def test_happy_path(
        self,
        smart_asa_contract: Contract,
        smart_asa_app: AppAccount,
        smart_asa_id: int,
        creator: Account,
        opted_in_account_factory: Callable,
    ) -> None:

        print(f"\n --- Getting 'frozen' param of Smart ASA {smart_asa_app.app_id}...")
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["frozen"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="is_asset_frozen",
        )

        account = opted_in_account_factory()
        account_local_state = get_local_state(
            account.algod_client, account.address, smart_asa_app.app_id
        )
        print(f"\n --- Getting 'frozen' param of Account {account.address}...")
        assert account_local_state["frozen"] == smart_asa_get_asset_frozen(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="is_account_frozen",
            account=account,
        )

        print(f"\n --- Getting 'total' param of Smart ASA {smart_asa_app.app_id}...")
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["total"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_total",
        )

        print(f"\n --- Getting 'decimals' param of Smart ASA {smart_asa_app.app_id}...")
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["decimals"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_decimals",
        )

        print(
            f"\n --- Getting 'unit_name' param of Smart ASA {smart_asa_app.app_id}..."
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["unit_name"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_unit_name",
        )

        print(f"\n --- Getting 'name' param of Smart ASA {smart_asa_app.app_id}...")
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["name"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_asset_name",
        )

        print(f"\n --- Getting 'url' param of Smart ASA {smart_asa_app.app_id}...")
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["url"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_url",
        )

        print(
            f"\n --- Getting 'metadata_hash' param of Smart ASA {smart_asa_app.app_id}..."
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["metadata_hash"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_metadata_hash",
        )

        print(
            f"\n --- Getting 'manager_addr' param of Smart ASA {smart_asa_app.app_id}..."
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["manager_addr"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_manager_addr",
        )

        print(
            f"\n --- Getting 'reserve_addr' param of Smart ASA {smart_asa_app.app_id}..."
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["reserve_addr"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_reserve_addr",
        )

        print(
            f"\n --- Getting 'freeze_addr' param of Smart ASA {smart_asa_app.app_id}..."
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["freeze_addr"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_freeze_addr",
        )

        print(
            f"\n --- Getting 'clawback_addr' param of Smart ASA {smart_asa_app.app_id}..."
        )
        smart_asa = get_smart_asa_params(creator.algod_client, smart_asa_id)
        assert smart_asa["clawback_addr"] == smart_asa_get(
            smart_asa_contract=smart_asa_contract,
            smart_asa_app=smart_asa_app,
            caller=creator,
            asset_id=smart_asa_id,
            getter="get_clawback_addr",
        )
