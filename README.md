# Smart-ASA

Smart ASA reference implementation that combines the simplicity and security of an Algorand Standard Asset with the composability and programmability of Algorand Smart Contracts to obtain a new, powerful, L1 entity that extends a regular ASA up to the limits of your imagination!

## Overview

The Smart ASA introduced with [ARC-0020](https://github.com/aldur/ARCs/blob/smartasa/ARCs/arc-0020.md) represents a new building block for complex blockchain applications. It offers a more flexible way to work with ASAs providing re-configuration functionalities and the possibility of building additional business logics around operations like ASA transfers, mints, and burns. This example presents an implementation of the Smart ASA contract as well as an easy to use CLI to interact with its functionalities.

**⚠️ Disclamer: This code is not audited!**

## Reference implementation rational

A Smart ASA is an ASA, called *Underlying ASA*, controlled by a Smart Contract, called *Smart ASA App*, that exposes methods to `create`, `configure`, `transfer`, `freeze`, and `destroy` the asset. The `create` method initializes the state of the controlling Smart Contract and creates the *Underlying ASA*. The following sections introduce the configurations used by this reference implementation for both the *Underlying ASA* and the Application state.

### Underlying ASA configuration

The `create` method of the Smart ASA App triggers an `AssetConfigTx` transaction (inner transaction) that creates a new asset with the following parameters:

| Property         | Value                  |
|------------------|------------------------|
| `total`          | 2^61-1                 |
| `decimals`       | 0                      |
| `default_frozen` | True                   |
| `unit_name`      | S-ASA                  |
| `asset_name`     | SMART-ASA              |
| `url`            | \<Smart ASA App ID\>   |
| `manager_addr`   | \<Smart ASA App Addr\> |
| `reserve_addr`   | \<Smart ASA App Addr\> |
| `freeze_addr`    | \<Smart ASA App Addr\> |
| `clawback_name`  | \<Smart ASA App Addr\> |

The underlying ASA is created with maximum supply (max `uint64`), it is not divisible, and it is frozen by default. The unit and asset names are custom strings that identify the Smart ASA, whereas the `url` field is used to link the ASA with the Smart ASA App Id. Finally, the `manager`, `reserve`, `freeze`, and `clawback` roles of the ASA are assigned to the application address. Therefore, the underlying ASA can only be controlled by the smart contract.

### State Schema

The `SateSchema` of the Smart Contract implementing a Smart ASA App has been designed to match 1-to-1 the parameters of an ASA. In addition, this reference implementation requires users to opt-in to the application and initialize their `LocalState`.

#### Global State

The `GlobalState` of the Smart ASA App in this reference implementation is defined as follows:

**Integer Variables**

- `total`: available total supply of a Smart ASA. This value cannot be greater than the underlying ASA total supply;
- `decimals`: number of digits to use after the decimal point. If 0, the Smart ASA is not divisible. If 1, the base unit of the Smart ASA is in tenth, it 2 it is in hundreds, if 3 it is in thousands, and so on;
- `default_frozen`: True to freeze Smart ASA holdings by default;
- `smart_asa_id`: asset ID of the underlying ASA;
- `frozen`: True to globally freeze Smart ASA transfers for all holders.

**Bytes Variables**

- `unit_name`: name of a unit of the Smart ASA;
- `name`: name of the Smart ASA;
- `url`: URL with additional information on the Smart ASA;
- `metadata_hash`: Smart ASA metadata hash;
- `manager_addr`: Address of the account that can manage the configuration of the Smart ASA and destroy it;
- `reserve_addr`: Address of the account holding the reserve (non-minted) units of the Smart ASA;
- `freeze_addr`: Address of the account used to freeze holdings or even globally freeze the Smart ASA;
- `clawback_addr`: Address of the account that can clawback holdings of the Smart ASA.

The Smart ASA App of the reference implementation has been designed to control one ASA at a time. For this reason, the `smart_asa_id` variable has been added to the `GlobalState`. It is used to record the current underlying ASA controlled by the application. This value is also stored into the local state of opted-in users, enforcing cross-checks between local and global states and avoiding issues like unauthorized transfers (see Security Considerations for more details).

This reference implementation also includes the Smart ASA global `frozen` variable. It can be updated only by the freeze address which can now globally freeze the asset through a single action, rather than freezing accounts one by one.

In this implementation, new functional authority has been assigned to the `reserve` address of the Smart ASA, which is now the (only) entity in charge of `minting` and `burning` Smart ASAs (see the Smart ASA Transfer interface for more details).

#### Local State

The `LocalState` initialized by the Smart ASA App for opted-in users is defined as follows:

**Integer Variables**

- `smart_asa_id`: asset ID of the underlying ASA of the Smart ASA a user has opted-in;
- `frozen`: True to freeze the holdings of the account.

#### Self Validation

The Smart ASA reference implementation enforces self validation of the `StateSchema`. On creation, it controls the size oth the given schema for both the global and local states. The expected values are:

- `GlobalState(Ints)` = 5
- `GlobalState(Bytes)` = 8
- `LocalState (Ints)` = 2
- `LocalState (Bytes)` = 0

#### Smart Contract ABI's type check

Smart Contract methods has been implemented to comply with the Algorand ABI interface. The validation checks on the ABI types are carried on the client side. The Smart Contract enforces the following on-chain checks:

- `address` length must be equal to 32 bytes;
- `Bool` values must be equal to 0 or 1.

## Smart ASA Methods

Smart ASA reference implementation follows the ABI specified by ARC-20 to
ensure full composability and interoperability with the rest of
Algorand's ecosystem (e.g. wallets, chain explorers, external dApp, etc.).

The implementation of the ABI relies on the new PyTeal ABI Router, which
automatically generates ABI JSON by using simple Python _decorators_ for Smart
Contract methods. PyTeal ABI Router takes care of ABI types and methods'
signatures encoding as well.

### Smart ASA App Create

Smart ASA Create is a `BareCall` (no argument needed) that instantiate the Smart
ASA App, verifying the consistency of the `SateSchema` assigned to the create
Application Call. This method initializes the whole Global State to default
upon creation.

### Smart ASA App Opt-In

Smart ASA Opt-In

```json
{
  "name": "asset_app_optin",
  "args": [{"type": "asset", "name": "asset_id"}],
  "returns": {"type": "void"}
}
```

### Smart ASA App Close-Out
```json
{
  "name": "asset_app_closeout",
  "args": [{"type": "asset"}],
  "returns": {"type": "void"}
}
```

### Smart ASA Creation
```json
{
  "name": "asset_create",
  "args": [
    {"type": "uint64"},
    {"type": "uint32"},
    {"type": "bool"},
    {"type": "string"},
    {"type": "string"},
    {"type": "string"},
    {"type": "string"},
    {"type": "address"},
    {"type": "address"},
    {"type": "address"},
    {"type": "address"}
  ],
  "returns": {"type": "uint64"}
}
```

### Smart ASA Configuration
```json
{
  "name": "asset_config",
  "args": [
    {"type": "asset"},
    {"type": "uint64"},
    {"type": "uint32"},
    {"type": "bool"},
    {"type": "string"},
    {"type": "string"},
    {"type": "string"},
    {"type": "string"},
    {"type": "address"},
    {"type": "address"},
    {"type": "address"},
    {"type": "address"}
  ],
  "returns": {"type": "void"}
}
```

### Smart ASA Transfer
```json
{
  "name": "asset_transfer",
  "args": [
    {"type": "asset"},
    {"type": "uint64"},
    {"type": "account"},
    {"type": "account"}
  ],
  "returns": {"type": "void"}
}
```

#### Minting

#### Burning

#### Clawback

#### Transfer

### Smart ASA Global Freeze
```json
{
  "name": "asset_freeze",
  "args": [
    {"type": "asset"},
    {"type": "bool"}
  ],
  "returns": {"type": "void"}
}
```

### Smart ASA Account Freeze
```json
{
  "name": "account_freeze",
  "args": [
    {"type": "asset"},
    {"type": "account"},
    {"type": "bool"}
  ],
  "returns": {"type": "void"}
}
```

### Smart ASA Destroy
```json
{
  "name": "asset_destroy",
  "args": [
    {"type": "asset"}
  ],
  "returns": {"type": "void"}
}
```

### Smart ASA Getters

## Smart ASA life-cycle example

### Smart ASA CLI - Install
The `Pipfile` contains all the dependencies to install the Smart ASA CLI using
`pipenv` entering:

```shell
pipenv install
```

The Smart ASA CLI requires an Algorand `sandbox` up and running (try it in
`dev` mode first!).

### Smart ASA CLI - Usage
The Smart ASA CLI plays the same role as `goal asset` to facilitate a seamless
understanding of this new "smarter" ASA.

The CLI has been built with `docopt`, which provides an intuitive and standard
command line usage:

- `<...>` identify mandatory positional arguments;
- `[...]` identify optional arguments;
- `(...|...)` identify mandatory mutually exclusive arguments;
- `[...|...]` identify optional mutually exclusive arguments;
- `--arguments` could be followed by a `<value>` (if required) or not;

All the `<account>`s (e.g. `<creator>`, `<manager>`, etc.) must be addresses of
a wallet account managed by `sandbox`'s KMD.

Using the command line you can perform all the actions over a Smart ASA, just
like an ASA!

```shell
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
```

### Create Smart ASA NFT
Let's create a beautiful 🔴 Smart ASA NFT (non-fractional for the moment)...

```shell
python3 smart_asa.py create KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ 1 --name Red --unit-name 🔴

 --- Creating Smart ASA App...
 --- Smart ASA App ID: 2988

 --- Funding Smart ASA App with 1 ALGO...

 --- Creating Smart ASA...
 --- Created Smart ASA with ID: 2991
```

The Smart ASA is created directly by the Smart ASA App, so upon creation the
whole supply is stored in Smart ASA App account. A *minting* action is required
to put units of Smart ASA in circulation (see
[Mint Smart ASA NFT](./README.md#mint-smart-asa-nft)).

```shell
python3 smart_asa.py info 2991

        Asset ID:         2991
        App ID:           2988
        App Address:      T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
        Creator:          KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Asset name:       Red

        Unit name:        🔴

        Maximum issue:    1 🔴
        Issued:           0 🔴
        Decimals:         0
        Global frozen:    False
        Default frozen:   False
        Manager address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Reserve address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Freeze address:   KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Clawback address: KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
```

### Fractionalize Smart ASA NFT
One of the amazing new feature of Smart ASAs is that they are **completely**
re-configurable after creation! Exactly: you can even reconfigure their
`total` or their `decimals`!

So let's use this new cool feature to **fractionalize** the Smart ASA NFT after
its creation by setting the new `<total>` to 100 and `<decimals>` to 2!

```shell
python3 smart_asa.py config 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ --total 100 --decimals 2

 --- Configuring Smart ASA 2991...
 --- Smart ASA 2991 configured!
```

```shell
python3 smart_asa.py info 2991

        Asset ID:         2991
        App ID:           2988
        App Address:      T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
        Creator:          KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Asset name:       Red

        Unit name:        🔴

        Maximum issue:    100 🔴 <-- 😱
        Issued:           0 🔴
        Decimals:         2      <-- 😱
        Global frozen:    False
        Default frozen:   False
        Manager address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Reserve address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Freeze address:   KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Clawback address: KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
```

### Smart ASA NFT opt-in
We can now opt-in the Smart ASA using the `optin` command that manages both the
undelying ASA opt-in and the Smart ASA App opt-in under the hood.

> Note that opt-in to Smart ASA App is required only if the Smart ASA need
> local state (e.g. *account frozen*).

```shell
python3 smart_asa.py optin 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ

 --- Opt-in Smart ASA 2991...

 --- Smart ASA 2991 state:
{'frozen': 0, 'smart_asa_id': 2991}
```

### Mint Smart ASA NFT
Only Smart ASA Reserve Address can mint units of Smart ASA from the Smart ASA
App, with the following restrictions:

- Smart ASA can not be *over minted* (putting in circulation more units than
`total`);
- Smart ASA can not be minted if the *asset is global frozen*;
- Smart ASA can not be minted if the minting receiver *account is frozen*;

```shell
python3 smart_asa.py send 2991 T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ 100
--reserve KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ

 --- Minting 100 units of Smart ASA 2991
 from T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
 to KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ...
 --- Confirmed!
```

```shell
python3 smart_asa.py info 2991

        Asset ID:         2991
        App ID:           2988
        App Address:      T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
        Creator:          KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Asset name:       Red

        Unit name:        🔴

        Maximum issue:    100 🔴
        Issued:           100 🔴 <-- 👀
        Decimals:         2
        Global frozen:    False
        Default frozen:   False
        Manager address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Reserve address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Freeze address:   KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Clawback address: KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
```

### Smart NFT ASA global freeze
Differently from regular ASA, Smart ASA can now be *globally frozen* by Freeze
Account, meaning that the whole Smart ASA in atomically frozen regardless the
particular *frozen state* of each account (which continues to be managed in
the same way as regular ASA).

Let's freeze the whole Smart ASA before starting administrative operations on
it:

```shell
python3 smart_asa.py freeze 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ --asset 1

 --- Freezing Smart ASA 2991...
```

```shell
python3 smart_asa.py info 2991

        Asset ID:         2991
        App ID:           2988
        App Address:      T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
        Creator:          KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Asset name:       Red

        Unit name:        🔴

        Maximum issue:    100 🔴
        Issued:           100 🔴
        Decimals:         2
        Global frozen:    True   <-- 😱
        Default frozen:   False
        Manager address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Reserve address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Freeze address:   KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Clawback address: KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
```

### Smart NFT ASA rename
Now that the whole Smart ASA is globally frozen, let's take advantage again of
Smart ASA full reconfigurability to change its `--name` and `--unit-name`!

```shell
python3 smart_asa.py config 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ --name Blue --unit-name 🔵

 --- Configuring Smart ASA 2991...
 --- Smart ASA 2991 configured!
```

```shell
python3 smart_asa.py info 2991

        Asset ID:         2991
        App ID:           2988
        App Address:      T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
        Creator:          KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Asset name:       Blue   <-- 😱

        Unit name:        🔵     <-- 😱

        Maximum issue:    100 🔵
        Issued:           100 🔵
        Decimals:         2
        Global frozen:    True
        Default frozen:   False
        Manager address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Reserve address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Freeze address:   KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Clawback address: KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
```

### Smart NFT ASA global unfreeze
The Smart ASA is all set! Let's *unfreeze* it globally!

```shell
python3 smart_asa.py freeze 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ --asset 0

 --- Unfreezing Smart ASA 2991...
```

```shell
python3 smart_asa.py info 2991

        Asset ID:         2991
        App ID:           2988
        App Address:      T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
        Creator:          KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Asset name:       Blue

        Unit name:        🔵

        Maximum issue:    100 🔵
        Issued:           100 🔵
        Decimals:         2
        Global frozen:    False  <-- 😱
        Default frozen:   False
        Manager address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Reserve address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Freeze address:   KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Clawback address: KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
```

### Smart NFT ASA burn
Another exclusive capability of Smart ASA Reserve Address is *burning* the
Smart ASA with the following limitation:

- Smart ASA can not be burned if the *asset is global frozen*;
- Smart ASA can not be burned if the Reserve *account is frozen*;

```shell
python3 smart_asa.py send 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU 100
--reserve KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ

 --- Burning 100 units of Smart ASA 2991
 from KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
 to T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU...
 --- Confirmed!
```

```shell
python3 smart_asa.py info 2991

        Asset ID:         2991
        App ID:           2988
        App Address:      T6QBA5AXSJMBG55Y2BVDR6MN5KTXHHLU7LWDY3LGZNAPGIKDOWMP4GF5PU
        Creator:          KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Asset name:       Blue

        Unit name:        🔵

        Maximum issue:    100 🔵
        Issued:           0 🔵    <-- 👀
        Decimals:         2
        Global frozen:    False
        Default frozen:   False
        Manager address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Reserve address:  KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Freeze address:   KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
        Clawback address: KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ
```

### Smart ASA destroy
Similarly to regular ASA, Smart ASA can be destroyed by Smart ASA Manager
Address if and only if the Smart ASA Creator hold the `total` supply.

```shell
python3 smart_asa.py destroy 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ

 --- Destroying Smart ASA 2991...
 --- Smart ASA 2991 destroyed!
```

## Security Considerations

> Explain why the ref. implementation stores on-chain the underlying asa is both on local and global storage. Give an example with Eve and Smart ASA A / Smart ASA B

## Conclusions

Smart ASA reference implementation is a building block that shows how regular
ASA can be turned into a more poweful and sophisticated L1 tool. By adopting
ABI the Smart ASA will be easily interoperable and composable with the rest of
Algorand's ecosystem (e.g. wallets, chain explorers, external dApp, etc.).

This reference implementation is intended to be used as initial step for more
specific and customized transferability logic like: royalties, DAOs' assets,
NFTs, in-game assets etc.

We encourage the community to expand and customize this new tool to fit
specific dApp!

Enjoy experimenting and building with Smart ASA!
