"""
Smart ASA (ARC-20 reference implementation)

Usage:
  smart_asa create  <creator> <total> [--decimals=<d>] [--default-frozen=<df>]
                    [--name=<n>] [--unit-name=<un>] [--metadata-hash=<mh>]
                    [--url=<l>] [--manager=<m>] [--reserve=<r>]
                    [--freeze=<f>] [--clawback=<c>]
  smart_asa config  <asset-id> <manager> [--total=<t>] [--decimals=<d>]
                    [--default-frozen=<df>] [--name=<n>] [--unit-name=<un>]
                    [--metadata-hash=<mh>] [--url=<u>] [--manager=<m>]
                    [--reserve=<r>] [--freeze=<f>] [--clawback=<c>]
  smart_asa destroy <asset-id> <manager>
  smart_asa freeze  <asset-id> <freeze> (--asset | <account>) <boolean>
  smart_asa optin   <asset-id> <account>
  smart_asa optout  <asset-id> <account> <close-to>
  smart_asa send    <asset-id> <from> <to> <amount>
                    [--minter=<i> | --clawback=<c>]
  smart_asa info    <asset-id> [--account=<a>]
  smart_asa get     <asset-id> <caller> <getter> [--account=<a>]
  smart_asa         [--help]

Commands:
  create     Create a Smart ASA
  config     Configure a Smart ASA
  destroy    Destroy a Smart ASA
  freeze     Freeze whole Smart ASA or specific account
  optin      Optin Smart ASAs
  optout     Optout Smart ASAs
  send       Transfer Smart ASAs
  info       Look up current parameters for Smart ASA or specific account
  get        Look up a parameter for Smart ASA

Options:
  -h, --help
"""

import sys
from docopt import docopt

from account import Account, AppAccount
from sandbox import Sandbox
from smart_asa_asc import (
    compile_stateful,
    smart_asa_abi,
)
from smart_asa_client import (
    get_smart_asa_params,
    smart_asa_account_freeze,
    smart_asa_app_closeout,
    smart_asa_app_create,
    smart_asa_app_optin,
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

    if args["<asset-id>"] is not None:
        args["<asset-id>"] = int(args["<asset-id>"])

    if args["--total"] is not None:
        args["--total"] = int(args["--total"])

    if args["--decimals"] is not None:
        args["--decimals"] = int(args["--decimals"])

    if args["--default-frozen"] is not None:
        args["--default-frozen"] = int(args["--default-frozen"])
        assert args["--default-frozen"] == 0 or args["--default-frozen"] == 1
        args["--default-frozen"] = bool(args["--default-frozen"])

    if args["<boolean>"] is not None:
        args["<boolean>"] = int(args["<boolean>"])
        assert args["<boolean>"] == 0 or args["<boolean>"] == 1
        args["<boolean>"] = bool(args["<boolean>"])

    if args["<amount>"] is not None:
        args["<amount>"] = int(args["<amount>"])

    return args


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
            asset_name=args["--name"],
            unit_name=args["--unit-name"],
            url=args["--url"],
            metadata_hash=args["--metadata-hash"],
            manager_addr=args["--manager"],
            reserve_addr=args["--reserve"],
            freeze_addr=args["--freeze"],
            clawback_addr=args["--clawback"],
        )
        return print(" --- Created Smart ASA with ID:", smart_asa_id, "\n")

    smart_asa = get_smart_asa_params(Sandbox.algod_client, args["<asset-id>"])
    smart_asa_app = AppAccount.from_app_id(app_id=smart_asa["app_id"])

    if args["config"]:
        manager = Sandbox.from_public_key(args["<manager>"])

        print(f"\n --- Configuring Smart ASA {args['<asset-id>']}...")
        smart_asa_config(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            manager=manager,
            asset_id=args["<asset-id>"],
            config_total=args["--total"],
            config_decimals=args["--decimals"],
            config_default_frozen=args[
                "--default-frozen"
            ],  # FIXME: turn it into a required arg
            config_asset_name=args["--name"],
            config_unit_name=args["--unit-name"],
            config_url=args["--url"],
            config_metadata_hash=args["--metadata-hash"],
            config_manager_addr=args["--manager"],
            config_reserve_addr=args["--reserve"],
            config_freeze_addr=args["--freeze"],
            config_clawback_addr=args["--clawback"],
        )
        return print(f" --- Smart ASA {args['<asset-id>']} configured!\n")

    if args["destroy"]:
        manager = Sandbox.from_public_key(args["<manager>"])

        print(f"\n --- Destroying Smart ASA {args['<asset-id>']}...")
        smart_asa_destroy(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            manager=manager,
            destroy_asset=args["<asset-id>"],
        )
        return print(f" --- Smart ASA {args['<asset-id>']} destroyed!\n")

    if args["freeze"]:
        freezer = Sandbox.from_public_key(args["<freeze>"])

        if args["<boolean>"]:
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
                asset_frozen=args["<boolean>"],
            )
        else:
            print(f"\n --- {action} account {args['<account>']}...\n")
            return smart_asa_account_freeze(
                smart_asa_contract=contract,
                smart_asa_app=smart_asa_app,
                freezer=freezer,
                freeze_asset=args["<asset-id>"],
                account_frozen=args["<boolean>"],
                target_account=args["<account>"],
            )

    if args["optin"]:
        account = Sandbox.from_public_key(args["<account>"])

        print(f"\n --- Opt-in Smart ASA {args['<asset-id>']}...")
        account.optin_to_asset(args["<asset-id>"])
        smart_asa_app_optin(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            asset_id=args["<asset-id>"],
            caller=account,
        )
        print(f"\n --- Smart ASA {args['<asset-id>']} state:")
        return print(account.app_local_state(smart_asa_app.app_id), "\n")

    if args["optout"]:
        account = Sandbox.from_public_key(args["<account>"])
        close_to = Account(address=args["<close-to>"])

        print(f"\n --- Closing Smart ASA {args['<asset-id>']}...")
        account.close_asset_to(args["<asset-id>"], close_to)
        smart_asa_app_closeout(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            asset_id=args["<asset-id>"],
            closer=account,
        )
        return print(f"\n --- Smart ASA {args['<asset-id>']} closed!")

    if args["send"]:
        if args["--minter"]:
            caller = Sandbox.from_public_key(args["--minter"])
            action = "Minting"
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

    if args["info"]:
        if args["--account"]:
            account = Sandbox.from_public_key(args["--account"])
            print(f"\n --- Smart ASA {args['<asset-id>']} state:")
            return print(account.app_local_state(smart_asa_app.app_id), "\n")
        else:
            return smart_asa_info(args["<asset-id>"])

    if args["get"]:
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
            f"\n --- Smart ASA {args['<asset-id>']} " f"{args['<getter>']}: {result}\n"
        )


if __name__ == "__main__":
    smart_asa_cli()
