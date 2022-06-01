import dataclasses
from typing import Any, Optional, Union, cast

import algosdk
from algosdk import encoding, mnemonic
from algosdk.abi import Method
from algosdk.future import transaction
from algosdk.v2client import algod
from algosdk.atomic_transaction_composer import (
    TransactionSigner,
    TransactionWithSigner,
    AtomicTransactionComposer,
)

from utils import (
    assembly_program,
    get_global_state,
    get_local_state,
    get_params,
)


@dataclasses.dataclass(frozen=True)
class Account(TransactionSigner):
    address: str
    private_key: Optional[str] = None
    algod_client: Optional[algod.AlgodClient] = None

    def mnemonic(self) -> str:
        assert self.private_key
        return mnemonic.from_private_key(self.private_key)

    @classmethod
    def create(cls, **kwargs) -> "Account":
        private_key, address = algosdk.account.generate_account()
        return cls(cast(str, address), private_key, **kwargs)

    @property
    def decoded_address(self):
        return encoding.decode_address(self.address)

    def sign(self, txn):
        assert self.private_key
        return txn.sign(self.private_key)

    def sign_transactions(
        self, txn_group: list[transaction.Transaction], indexes: list[int]
    ) -> list:
        # Enables using `self` with `AtomicTransactionComposer`
        stxns = []
        for i in indexes:
            stxn = self.sign(txn_group[i])  # type: ignore
            stxns.append(stxn)
        return stxns

    def sign_send_wait(self, txn: transaction.Transaction, save_txn: str = None):
        """Sign a transaction, submit it, and wait for its confirmation."""
        assert self.algod_client

        signed_txn = self.sign(txn)
        tx_id = signed_txn.transaction.get_txid()
        if save_txn:
            transaction.write_to_file([signed_txn], save_txn, overwrite=True)

        try:
            self.algod_client.send_transactions([signed_txn])
            # TODO: `wait_for_confirmation` doesn't work with `dev` mode in
            #  Sandbox we should consider a `debug` flag to disable it.

            # transaction.wait_for_confirmation(self.algod_client, tx_id)
            return self.algod_client.pending_transaction_info(tx_id)

        except algosdk.error.AlgodHTTPError as err:
            drr = transaction.create_dryrun(self.algod_client, [signed_txn])
            filename = "/tmp/dryrun.msgp"
            with open(filename, "wb") as f:
                import base64

                f.write(base64.b64decode(encoding.msgpack_encode(drr)))
            raise err

    def _get_params(self, *args, **kwargs) -> transaction.SuggestedParams:
        assert self.algod_client
        return get_params(self.algod_client, *args, **kwargs)

    def pay(self, receiver: Union["Account", "AppAccount"], amount: int):
        txn = transaction.PaymentTxn(
            self.address, self._get_params(), receiver.address, amount
        )
        return self.sign_send_wait(txn)

    def abi_call(
        self,
        method: Method,
        *args,
        app: Optional[Union[int, "AppAccount"]] = None,
        group_extra_txns: Optional[list[TransactionWithSigner]] = None,
        on_complete: transaction.OnComplete = transaction.OnComplete.NoOpOC,
        fee: Optional[int] = None,
        extra_app_call_nop: int = 0,
        max_wait_rounds: int = 10,
        save_abi_call: str = None
    ) -> Any:  # TODO: Correctly specify the return type here.
        """
        ABI call from `sender` to `app` `method`, with `*args`. Txn-type args are supplied
        as normal arguments.
        Use `group_extra_txns` to append other (non argument) transactions to the ABI call in an
        atomic group.
        """
        assert self.algod_client

        if app is None:
            if hasattr(method, "__self__") and hasattr(method.__self__, "__app_id__"):
                app = getattr(method.__self__, "__app_id__")
            else:
                raise ValueError(
                    "app parameter required for abi call to unbounded methods"
                )
        if isinstance(app, AppAccount):
            app = app.app_id

        encoded_args = []
        for arg in args:
            if isinstance(arg, Account):
                encoded_args.append(arg.address)
            else:
                encoded_args.append(arg)

        atc = AtomicTransactionComposer()
        atc.add_method_call(
            app_id=app,
            method=method,
            method_args=encoded_args,
            sp=self._get_params(fee),
            sender=self.address,
            signer=self,
            on_complete=on_complete,
        )

        if group_extra_txns is not None:
            for transaction_with_signer in group_extra_txns:
                atc.add_transaction(transaction_with_signer)

        if extra_app_call_nop:
            for i in range(extra_app_call_nop):
                atc.add_transaction(
                    TransactionWithSigner(
                        transaction.ApplicationNoOpTxn(
                            sender=self.address,
                            sp=self._get_params(fee),
                            index=app,
                            note=bytes(i),
                        ),
                        self,
                    )
                )

        atc.build_group()
        atc.gather_signatures()
        if save_abi_call:
            transaction.write_to_file(atc.signed_txns, save_abi_call, overwrite=True)
        try:
            atc_result = atc.execute(self.algod_client, max_wait_rounds)
            logged_result = atc_result.abi_results[0]  # type: ignore
            if logged_result.decode_error:
                print("ABI decode error:", logged_result.decode_error)
                print("\tRaw value:", logged_result.raw_value)
            if not logged_result or logged_result.return_value is None:
                return None
            return logged_result.return_value

        except algosdk.error.AlgodHTTPError as err:
            drr = transaction.create_dryrun(self.algod_client, atc.signed_txns)
            filename = "/tmp/dryrun.msgp"
            with open(filename, "wb") as f:
                import base64

                f.write(base64.b64decode(encoding.msgpack_encode(drr)))
            raise err

    def create_asset(self, **kwargs) -> int:
        """Create an asset and return its ID."""
        args = {
            "sp": self._get_params(),
            "total": 1,
            "default_frozen": False,
            "unit_name": "TMP",
            "asset_name": "TMP",
            "manager": self.address,
            "reserve": self.address,
            "freeze": self.address,
            "clawback": self.address,
            "decimals": 6,
        }
        args.update(**kwargs)
        txn = transaction.AssetConfigTxn(sender=self.address, **args)

        ptx = self.sign_send_wait(txn)
        return ptx["asset-index"]

    def optin_to_asset(self, asset_id: int):
        txn = transaction.AssetTransferTxn(
            sender=self.address,
            sp=self._get_params(),
            receiver=self.address,
            amt=0,
            index=asset_id,
        )
        return self.sign_send_wait(txn)

    def close_asset_to(self, asset_id: int, close_to_account: "Account"):
        txn = transaction.AssetTransferTxn(
            sender=self.address,
            sp=self._get_params(),
            receiver=self.address,
            amt=0,
            index=asset_id,
            close_assets_to=close_to_account.address,
        )
        return self.sign_send_wait(txn)

    def optin_to_application(
        self,
        asc_id: int,
        app_args: Any = None,
        accounts: Any = None,
        foreign_apps: Any = None,
        foreign_assets: Any = None,
    ):
        txn = transaction.ApplicationOptInTxn(
            sender=self.address,
            sp=self._get_params(),
            index=asc_id,
            app_args=app_args,
            accounts=accounts,
            foreign_apps=foreign_apps,
            foreign_assets=foreign_assets,
        )
        return self.sign_send_wait(txn)

    def transfer_asset(self, receiver: "Account", asset_id: int, amount: int):
        txn = transaction.AssetTransferTxn(
            sender=self.address,
            sp=self._get_params(),
            receiver=receiver.address,
            amt=amount,
            index=asset_id,
        )
        return self.sign_send_wait(txn)

    def close_out_application(self, app_id: int):
        txn = transaction.ApplicationCloseOutTxn(
            self.address, self._get_params(), app_id
        )
        return self.sign_send_wait(txn)

    def balance(self) -> dict[int, int]:
        """Returns a dict mappgin each asset id to the balance amount; the algo balance has key 0."""
        assert self.algod_client
        account_info = self.algod_client.account_info(self.address)
        balances = {a["asset-id"]: int(a["amount"]) for a in account_info["assets"]}
        balances[0] = int(account_info["amount"])
        return balances

    def asa_balance(self, asa_idx: int) -> int:
        return self.balance().get(asa_idx, 0)

    def app_local_state(
        self, app: Union["AppAccount", int]
    ) -> dict[str, Union[bytes, int]]:
        assert self.algod_client
        if isinstance(app, AppAccount):
            app = app.app_id
        return get_local_state(self.algod_client, self.address, app)

    def local_state(self) -> list[dict]:
        assert self.algod_client
        return self.algod_client.account_info(self.address)["apps-local-state"]

    def create_asc(
        self,
        approval_program: str,
        clear_program: str,
        global_schema=transaction.StateSchema(0, 0),
        local_schema=transaction.StateSchema(0, 0),
        on_complete=transaction.OnComplete.NoOpOC,
    ) -> "AppAccount":
        approval_program = assembly_program(self.algod_client, approval_program)
        clear_program = assembly_program(self.algod_client, clear_program)

        txn = transaction.ApplicationCreateTxn(
            self.address,
            self._get_params(),
            on_complete,
            approval_program,
            clear_program,
            global_schema,
            local_schema,
            extra_pages=(len(approval_program) + len(clear_program)) // 2048,
        )

        transaction_response = self.sign_send_wait(txn)
        return AppAccount.from_app_id(
            transaction_response["application-index"], algod_client=self.algod_client
        )


@dataclasses.dataclass(frozen=True)
class LsigAccount(Account):
    lsig: transaction.LogicSig = None

    @classmethod
    def from_lsig(cls, lsig, **kwargs) -> "LsigAccount":
        return cls(lsig=lsig, **kwargs)

    def sign(self, txn):
        return transaction.LogicSigTransaction(txn, self.lsig)  # type: ignore


@dataclasses.dataclass(frozen=True)
class AppAccount(Account):
    app_id: int = None

    @classmethod
    def from_app_id(cls, app_id: int, **kwargs) -> "AppAccount":
        return cls(
            app_id=app_id,
            address=cast(
                str,
                encoding.encode_address(
                    encoding.checksum(b"appID" + app_id.to_bytes(8, "big"))
                ),
            ),
            **kwargs
        )

    def global_state(self) -> dict[str, Union[bytes, int]]:
        assert self.algod_client
        return get_global_state(self.algod_client, self.app_id)

    def app_local_state(
        self, account: Union[Account, str]
    ) -> dict[str, Union[bytes, int]]:
        assert self.algod_client
        if isinstance(account, Account):
            account = account.address
        return get_local_state(self.algod_client, account, self.app_id)
