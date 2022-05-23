"""Smart ASA test suite"""

import pytest

from pyteal import Expr

from smart_asa_asc import (
    _asc_approval,
    _asc_clear,
    compile_stateful,
)


@pytest.fixture()
def approval_porgram() -> Expr:
    return _asc_approval()


@pytest.fixture()
def clear_porgram() -> Expr:
    return _asc_clear()


def test_compile(approval_porgram: Expr, clear_porgram: Expr) -> None:
    # This test simply ensures we can compile the ASC programs
    teal_approval_program = compile_stateful(approval_porgram)
    teal_clear_program = compile_stateful(clear_porgram)

    print("\nAPPROVAL PROGRAM\n" + teal_approval_program)
    with open("/tmp/approval.teal", "w") as f:
        f.write(teal_approval_program)

    print("\nCLEAR PROGRAM\n" + teal_clear_program)
    with open("/tmp/clear.teal", "w") as f:
        f.write(teal_clear_program)
