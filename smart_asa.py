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

from sandbox import Sandbox
from smart_asa_client import get_smart_asa_params


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


def smart_asa_cli():
    if len(sys.argv) == 1:
        # Display help if no arguments, see:
        # https://github.com/docopt/docopt/issues/420#issuecomment-405018014
        sys.argv.append("--help")

    args = docopt(__doc__)

    if args["info"]:
        smart_asa_info(int(args["<asset-id>"]))


if __name__ == "__main__":
    smart_asa_cli()
