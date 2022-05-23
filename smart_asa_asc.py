"""
Smart ASA PyTEAL reference implementation based on ARC-20
"""

__author__ = (
    "Cosimo Bassi <cosimo.bassi@algorand.com>, "
    "Stefano De Angelis <stefano.deangelis@algorand.com>"
)

from pyteal import (
    Approve,
    Cond,
    Expr,
    Int,
    Mode,
    OnComplete,
    Reject,
    Txn,
    compileTeal,
)

TEAL_VERSION = 6


def on_create() -> Expr:
    return Approve()


def on_optin() -> Expr:
    return Reject()


def on_call() -> Expr:
    return Reject()


def on_closeout() -> Expr:
    return Reject()


def on_update() -> Expr:
    return Reject()


def on_delete() -> Expr:
    return Reject()


def _asc_approval() -> Expr:
    return Cond(
        [Txn.application_id() == Int(0), on_create()],
        [Txn.on_completion() == OnComplete.OptIn, on_optin()],
        [Txn.on_completion() == OnComplete.NoOp, on_call()],
        [Txn.on_completion() == OnComplete.CloseOut, on_closeout()],
        [Txn.on_completion() == OnComplete.UpdateApplication, on_update()],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete()],
    )


def _asc_clear() -> Expr:
    return Reject()


def compile_stateful(program: Expr) -> str:
    return compileTeal(
        program, Mode.Application, assembleConstants=True, version=TEAL_VERSION
    )


def compile_stateless(program: Expr) -> str:
    return compileTeal(
        program, Mode.Signature, assembleConstants=True, version=TEAL_VERSION
    )


if __name__ == "__main__":
    # Allow quickly testing compilation.
    from smart_asa_test import test_compile

    test_compile(_asc_approval(), _asc_clear())
