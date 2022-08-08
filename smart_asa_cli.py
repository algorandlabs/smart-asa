"""
Smart ASA (ARC-20 reference implementation)

Usage:
  smart_asa create  <creator> <total> [--decimals=<d>] [--default-frozen=<z>]
                    [--name=<n>] [--unit-name=<u>] [--metadata-hash=<s>]
                    [--url=<l>] [--manager=<m>] [--reserve=<r>]
                    [--freeze=<f>] [--clawback=<c>]
  smart_asa config  <asset-id> <manager> [--new-total=<t>] [--new-decimals=<d>]
                    [--new-default-frozen=<z>] [--new-name=<n>]
                    [--new-unit-name=<u>] [--new-metadata-hash=<s>]
                    [--new-url=<u>] [--new-manager=<m>] [--new-reserve=<r>]
                    [--new-freeze=<f>] [--new-clawback=<c>]
  smart_asa destroy <asset-id> <manager>
  smart_asa freeze  <asset-id> <freeze> (--asset | --account=<a>) <status>
  smart_asa optin   <asset-id> <account>
  smart_asa optout  <asset-id> <account> <close-to>
  smart_asa send    <asset-id> <from> <to> <amount>
                    [--reserve=<r> | --clawback=<c>]
  smart_asa info    <asset-id> [--account=<a>]
  smart_asa get     <asset-id> <caller> <getter> [--account=<a>]
  smart_asa         [--help]

Commands:
  create     Create a Smart ASA
  config     Configure a Smart ASA
  destroy    Destroy a Smart ASA
  freeze     Freeze whole Smart ASA or specific account, <status> = 1 is forzen
  optin      Optin Smart ASAs
  optout     Optout Smart ASAs
  send       Transfer Smart ASAs
  info       Look up current parameters for Smart ASA or specific account
  get        Look up a parameter for Smart ASA

Options:
  -h, --help
  -d, --decimals=<d>           [default: 0]
  -z, --default-frozen=<z>     [default: 0]
  -n, --name=<n>               [default: ]
  -u, --unit-name=<u>          [default: ]
  -l, --url=<l>                [default: ]
  -s, --metadata-hash=<s>      [default: ]
  -m, --manager=<m>            Default to Smart ASA Creator
  -r, --reserve=<r>            Default to Smart ASA Creator
  -f, --freeze=<f>             Default to Smart ASA Creator
  -c, --clawback=<c>           Default to Smart ASA Creator
"""

import sys
from docopt import docopt

from algosdk.abi import Contract

from account import Account, AppAccount
from sandbox import Sandbox
from smart_asa_asc import (
    compile_stateful,
    smart_asa_abi,
)
from smart_asa_client import (
    get_smart_asa_params,
    smart_asa_account_freeze,
    smart_asa_closeout,
    smart_asa_app_create,
    smart_asa_optin,
    smart_asa_create,
    smart_asa_config,
    smart_asa_destroy,
    smart_asa_freeze,
    smart_asa_get,
    smart_asa_transfer,
)


def smart_asa_info(smart_asa_id: int) -> None:
    smart_asa = get_smart_asa_params(Sandbox.algod_client, smart_asa_id)
    print(
        f"""
        Asset ID:         {smart_asa['smart_asa_id']}
        App ID:           {smart_asa['app_id']}
        App Address:      {smart_asa['app_address']}
        Creator:          {smart_asa['creator_addr']}
        Asset name:       {smart_asa['name']}

        Unit name:        {smart_asa['unit_name']}

        Maximum issue:    {smart_asa['total']} {smart_asa['unit_name']}
        Issued:           {smart_asa['circulating_supply']} {smart_asa['unit_name']}
        Decimals:         {smart_asa['decimals']}
        Global frozen:    {smart_asa['frozen']}
        Default frozen:   {smart_asa['default_frozen']}
        Manager address:  {smart_asa['manager_addr']}
        Reserve address:  {smart_asa['reserve_addr']}
        Freeze address:   {smart_asa['freeze_addr']}
        Clawback address: {smart_asa['clawback_addr']}
        """
    )


def args_types(args: dict) -> dict:
    if args["<total>"] is not None:
        args["<total>"] = int(args["<total>"])

    args["--decimals"] = int(args["--decimals"])

    args["--default-frozen"] = int(args["--default-frozen"])
    assert args["--default-frozen"] == 0 or args["--default-frozen"] == 1
    args["--default-frozen"] = bool(args["--default-frozen"])

    if args["<asset-id>"] is not None:
        args["<asset-id>"] = int(args["<asset-id>"])

    if args["--new-total"] is not None:
        args["--new-total"] = int(args["--new-total"])

    if args["--new-decimals"] is not None:
        args["--new-decimals"] = int(args["--new-decimals"])

    if args["--new-default-frozen"] is not None:
        args["--new-default-frozen"] = int(args["--new-default-frozen"])
        assert args["--new-default-frozen"] == 0 or args["--new-default-frozen"] == 1
        args["--new-default-frozen"] = bool(args["--new-default-frozen"])

    if args["<status>"] is not None:
        args["<status>"] = int(args["<status>"])
        assert args["<status>"] == 0 or args["<status>"] == 1
        args["<status>"] = bool(args["<status>"])

    if args["<amount>"] is not None:
        args["<amount>"] = int(args["<amount>"])

    return args


def asset_create(
    args: dict,
    approval: str,
    clear: str,
    contract: Contract,
) -> None:
    creator = Sandbox.from_public_key(args["<creator>"])

    print("\n --- Creating Smart ASA App...")
    smart_asa_app = smart_asa_app_create(approval, clear, creator)
    print(" --- Smart ASA App ID:", smart_asa_app.app_id)

    print("\n --- Funding Smart ASA App with 1 ALGO...")
    creator.pay(receiver=smart_asa_app, amount=1_000_000)

    print("\n --- Creating Smart ASA...")
    smart_asa_id = smart_asa_create(
        smart_asa_contract=contract,
        smart_asa_app=smart_asa_app,
        creator=creator,
        total=args["<total>"],
        decimals=args["--decimals"],
        default_frozen=args["--default-frozen"],
        name=args["--name"],
        unit_name=args["--unit-name"],
        url=args["--url"],
        metadata_hash=args["--metadata-hash"],
        manager_addr=args["--manager"],
        reserve_addr=args["--reserve"],
        freeze_addr=args["--freeze"],
        clawback_addr=args["--clawback"],
    )
    return print(" --- Created Smart ASA with ID:", smart_asa_id, "\n")


def asset_config(
    args: dict,
    contract: Contract,
    smart_asa_app: AppAccount,
) -> None:
    manager = Sandbox.from_public_key(args["<manager>"])

    print(f"\n --- Configuring Smart ASA {args['<asset-id>']}...")
    smart_asa_config(
        smart_asa_contract=contract,
        smart_asa_app=smart_asa_app,
        manager=manager,
        asset_id=args["<asset-id>"],
        config_total=args["--new-total"],
        config_decimals=args["--new-decimals"],
        config_default_frozen=args["--new-default-frozen"],
        config_name=args["--new-name"],
        config_unit_name=args["--new-unit-name"],
        config_url=args["--new-url"],
        config_metadata_hash=args["--new-metadata-hash"],
        config_manager_addr=args["--new-manager"],
        config_reserve_addr=args["--new-reserve"],
        config_freeze_addr=args["--new-freeze"],
        config_clawback_addr=args["--new-clawback"],
    )
    return print(f" --- Smart ASA {args['<asset-id>']} configured!\n")


def asset_destroy(
    args: dict,
    contract: Contract,
    smart_asa_app: AppAccount,
) -> None:
    manager = Sandbox.from_public_key(args["<manager>"])

    print(f"\n --- Destroying Smart ASA {args['<asset-id>']}...")
    smart_asa_destroy(
        smart_asa_contract=contract,
        smart_asa_app=smart_asa_app,
        manager=manager,
        destroy_asset=args["<asset-id>"],
    )
    return print(f" --- Smart ASA {args['<asset-id>']} destroyed!\n")


def asset_or_account_freeze(
    args: dict,
    contract: Contract,
    smart_asa_app: AppAccount,
) -> None:
    freezer = Sandbox.from_public_key(args["<freeze>"])

    if args["<status>"]:
        action = "Freezing"
    else:
        action = "Unfreezing"

    if args["--asset"]:
        print(f"\n --- {action} Smart ASA {args['<asset-id>']}...\n")
        return smart_asa_freeze(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            freezer=freezer,
            freeze_asset=args["<asset-id>"],
            asset_frozen=args["<status>"],
        )
    else:
        print(f"\n --- {action} account {args['--account']}...\n")
        return smart_asa_account_freeze(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            freezer=freezer,
            freeze_asset=args["<asset-id>"],
            account_frozen=args["<status>"],
            target_account=args["--account"],
        )


def asset_optin(
    args: dict,
    contract: Contract,
    smart_asa_app: AppAccount,
) -> None:
    account = Sandbox.from_public_key(args["<account>"])

    print(f"\n --- Opt-in Smart ASA {args['<asset-id>']}...")
    smart_asa_optin(
        smart_asa_contract=contract,
        smart_asa_app=smart_asa_app,
        asset_id=args["<asset-id>"],
        caller=account,
    )
    print(f"\n --- Smart ASA {args['<asset-id>']} state:")
    return print(account.app_local_state(smart_asa_app.app_id), "\n")


def asset_optout(
    args: dict,
    contract: Contract,
    smart_asa_app: AppAccount,
) -> None:
    account = Sandbox.from_public_key(args["<account>"])
    close_to = Account(address=args["<close-to>"])

    print(f"\n --- Closing Smart ASA {args['<asset-id>']}...")
    smart_asa_closeout(
        smart_asa_contract=contract,
        smart_asa_app=smart_asa_app,
        asset_id=args["<asset-id>"],
        caller=account,
        close_to=close_to,
    )
    return print(f"\n --- Smart ASA {args['<asset-id>']} closed!")


def asset_send(
    args: dict,
    contract: Contract,
    smart_asa_app: AppAccount,
) -> None:
    if args["--reserve"]:
        caller = Sandbox.from_public_key(args["--reserve"])
        if (
            args["<to>"] == args["--reserve"]
            and args["<from>"] == smart_asa_app.address
        ):
            action = "Minting"
        elif (
            args["<to>"] == smart_asa_app.address
            and args["<from>"] == args["--reserve"]
        ):
            action = "Burning"
        else:
            action = "Sending"
    elif args["--clawback"]:
        caller = Sandbox.from_public_key(args["--clawback"])
        action = "Clawbacking"
    else:
        caller = Sandbox.from_public_key(args["<from>"])
        action = "Sending"

    print(
        f"\n --- {action} {args['<amount>']} units of Smart ASA "
        f"{args['<asset-id>']} from {args['<from>']} to "
        f"{args['<to>']}..."
    )
    smart_asa_transfer(
        smart_asa_contract=contract,
        smart_asa_app=smart_asa_app,
        xfer_asset=args["<asset-id>"],
        asset_amount=args["<amount>"],
        caller=caller,
        asset_receiver=args["<to>"],
        asset_sender=args["<from>"],
    )
    return print(f" --- Confirmed!\n")


def asset_or_account_info(
    args: dict,
    smart_asa_app: AppAccount,
) -> None:
    if args["--account"]:
        account = Account(address=args["--account"])
        print(f"\n --- Smart ASA {args['<asset-id>']} state:")
        return print(account.app_local_state(smart_asa_app.app_id), "\n")
    else:
        return smart_asa_info(args["<asset-id>"])


def asset_get(
    args: dict,
    contract: Contract,
    smart_asa_app: AppAccount,
) -> None:
    caller = Sandbox.from_public_key(args["<caller>"])
    result = smart_asa_get(
        smart_asa_contract=contract,
        smart_asa_app=smart_asa_app,
        caller=caller,
        asset_id=args["<asset-id>"],
        getter=args["<getter>"],
        account=args["--account"],
    )
    return print(
        f"\n --- Smart ASA {args['<asset-id>']} " f"{args['<getter>']}: " f"{result}\n"
    )


def smart_asa_cli():
    if len(sys.argv) == 1:
        # Display help if no arguments, see:
        # https://github.com/docopt/docopt/issues/420#issuecomment-405018014
        sys.argv.append("--help")

    args = docopt(__doc__)
    args = args_types(args)

    approval, clear, contract = smart_asa_abi.build_program()
    approval = compile_stateful(approval)
    clear = compile_stateful(clear)

    if args["create"]:
        return asset_create(args, approval, clear, contract)
    else:
        smart_asa = get_smart_asa_params(Sandbox.algod_client, args["<asset-id>"])
        smart_asa_app = AppAccount.from_app_id(app_id=smart_asa["app_id"])

    if args["config"]:
        return asset_config(args, contract, smart_asa_app)
    elif args["destroy"]:
        return asset_destroy(args, contract, smart_asa_app)
    elif args["freeze"]:
        return asset_or_account_freeze(args, contract, smart_asa_app)
    elif args["optin"]:
        return asset_optin(args, contract, smart_asa_app)
    elif args["optout"]:
        return asset_optout(args, contract, smart_asa_app)
    elif args["send"]:
        return asset_send(args, contract, smart_asa_app)
    elif args["info"]:
        return asset_or_account_info(args, smart_asa_app)
    elif args["get"]:
        return asset_get(args, contract, smart_asa_app)
    else:
        return print("\n --- Wrong command. Enter --help for CLI usage!\n")


if __name__ == "__main__":
    smart_asa_cli()
