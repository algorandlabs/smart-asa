"""
Smart ASA (ARC-20 reference implementation)

Usage:
  smart_asa create  <creator> <total> [--default-frozen] [--decimals=<d>]
                    [--url=<u>] [--clawback=<c>] [--freeze=<f>] [--manager=<m>]
                    [--reserve=<r>] [--name=<n>] [--unit-name=<un>]
                    [--metadata-hash=<mh>]
  smart_asa config  <asset-id> <manager> [--decimals=<d>] [--url=<u>]
                    [--clawback=<c>] [--freeze=<f>] [--manager=<m>]
                    [--reserve=<r>] [--name=<n>] [--unit-name=<un>]
                    [--metadata-hash=<mh>]
  smart_asa destroy <asset-id> <manager>
  smart_asa freeze  <asset-id> <manager> [--asset-freeze=<af>] [--account=<a>]
  smart_asa optin   <asset-id> <account>
  smart_asa send    <asset-id> <from> <to> <amount> [--clawback=<c>]
  smart_asa info    <asset-id>
  smart_asa get     <asset-id> <getter>
  smart_asa         [--help]

Commands:
  create     Create a Smart ASA
  config     Configure a Smart ASA
  destroy    Destroy a Smart ASA
  freeze     Freeze Smart ASA or account
  optin      Optin to Smart ASAs
  send       Transfer Smart ASAs
  info       Look up current parameters for a Smart ASA

Options:
  -h, --help
"""

import sys
from docopt import docopt

from account import AppAccount
from sandbox import Sandbox
from smart_asa_asc import (
    compile_stateful,
    smart_asa_abi,
)
from smart_asa_client import (
    get_smart_asa_params,
    smart_asa_app_create,
    smart_asa_create,
    smart_asa_config,
    smart_asa_destroy,
)


def smart_asa_info(smart_asa_id: int) -> None:
    smart_asa = get_smart_asa_params(Sandbox.algod_client, smart_asa_id)
    print(
        f"""
        Asset ID:         {smart_asa['smart_asa_id']}
        App ID:           {smart_asa['app_id']}
        Creator:          {smart_asa['creator_addr']}
        Asset name:       {smart_asa['name']}

        Unit name:        {smart_asa['unit_name']}

        Maximum issue:    {smart_asa['total']} {smart_asa['unit_name']}
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

    if args["--decimals"] is not None:
        args["--decimals"] = int(args["--decimals"])

    return args


def smart_asa_cli():
    if len(sys.argv) == 1:
        # Display help if no arguments, see:
        # https://github.com/docopt/docopt/issues/420#issuecomment-405018014
        sys.argv.append("--help")

    args = docopt(__doc__)
    args = args_types(args)

    if args["info"]:
        smart_asa_info(int(args["<asset-id>"]))

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
        return print(" --- Created Smart ASA with ID:", smart_asa_id)

    if args["config"]:
        manager = Sandbox.from_public_key(args["<manager>"])
        smart_asa = get_smart_asa_params(manager.algod_client, args["<asset-id>"])
        smart_asa_app = AppAccount.from_app_id(app_id=smart_asa["app_id"])

        print(f"\n --- Configuring Smart ASA {args['<asset-id>']}...")
        smart_asa_config(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            manager=manager,
            asset_id=args["<asset-id>"],
            config_total=args["<total>"],
            config_decimals=args["--decimals"],
            config_default_frozen=args["--default-frozen"],
            config_asset_name=args["--name"],
            config_unit_name=args["--unit-name"],
            config_url=args["--url"],
            config_metadata_hash=args["--metadata-hash"],
            config_manager_addr=args["--manager"],
            config_reserve_addr=args["--reserve"],
            config_freeze_addr=args["--freeze"],
            config_clawback_addr=args["--clawback"],
        )
        return print(f" --- Smart ASA {args['<asset-id>']} configured!")

    if args["destroy"]:
        manager = Sandbox.from_public_key(args["<manager>"])
        smart_asa = get_smart_asa_params(manager.algod_client, args["<asset-id>"])
        smart_asa_app = AppAccount.from_app_id(app_id=smart_asa["app_id"])

        print(f"\n --- Destroying Smart ASA {args['<asset-id>']}...")
        smart_asa_destroy(
            smart_asa_contract=contract,
            smart_asa_app=smart_asa_app,
            manager=manager,
            destroy_asset=args["<asset-id>"],
        )
        return print(f" --- Smart ASA {args['<asset-id>']} destroyed!")


if __name__ == "__main__":
    smart_asa_cli()
