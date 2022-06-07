# Smart-ASA

Smart ASA reference implementation

## Overview

The Smart ASA introduced with [ARC-0020](https://github.com/aldur/ARCs/blob/smartasa/ARCs/arc-0020.md) represents a new building block for complex blockchain applications. It offers a more flexible way to work with ASAs providing re-configuration functionalities and the possibility of building additional business logics around operations like ASA transfers, mints, and burns. This example presents an implementation of the Smart ASA contract as well as an easy to use CLI to interact with its functionalities.

**Disclamer: This code is not audited and should not be used in a production environment.**

## Reference implementation rational

A Smart ASA is an ASA, called *underlying ASA*, controlled by a Smart Contract, called *Smart ASA APP*, that exposes methods to `create`, `configure`, `transfer`, `freeze`, and `destroy` the asset. The `create` method initializes the state of the controlling smart contract and creates the *underlying ASA*. The following sections introduce the configurations used by this reference implementation fof both the underlying ASA and the application state.

### Underlying ASA configuration

The `create` method of the Smart ASA App triggers an `AssetConfigTx` transaction (inner transaction) that creates a new asset with the following parameters:

- `Total`= (2**64)-1
- `Decimals`= 0
- `DefaultFrozen`= 1
- `UnitName`= "*S-ASA*"
- `AssetName`= "*SMART-ASA*"
- `URL`= \<*SmartASA_App_Id*\>
- `ManagerAddr`= \<*SmartASA_App_Addr*\>
- `ReserveAddr`= \<*SmartASA_App_Addr*\>
- `FreezeAddr`= \<*SmartASA_App_Addr*\>
- `ClawbackAddr`= \<*SmartASA_App_Addr*\>

The underlying ASA is created with maximum supply (max `uint64`), it is not divisible, and it is frozen by default. The unit and asset names are custom strings that identify the Smart ASA, whereas the `url` field is used to link the ASA with the Smart ASA App Id. Finally, the `manager`, `reserve`, `freeze`, and `clawback` roles of the ASA are assigned to the application address. Therefore, the underlying ASA can be only controlled by the smart contract.

### State Schema

#### Self Validation

#### Global State

#### Local State

### Smart Contract ABI's type check

### Smart ASA App Opt-In

### Smart ASA App Close-Out

### Smart ASA Configuration

### Smart ASA Transfer

#### Minting

#### Burning

#### Clawback

#### Transfer

### Smart ASA Global Freeze

## Smart ASA life-cycle example

### Smart ASA CLI - Install

### Smart ASA CLI - Usage

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

```shell
python3 smart_asa.py create KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ 1 --name Red --unit-name 🔴

 --- Creating Smart ASA App...
 --- Smart ASA App ID: 2988

 --- Funding Smart ASA App with 1 ALGO...

 --- Creating Smart ASA...
 --- Created Smart ASA with ID: 2991
```

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

```shell
python3 smart_asa.py optin 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ

 --- Opt-in Smart ASA 2991...

 --- Smart ASA 2991 state:
{'frozen': 0, 'smart_asa_id': 2991}
```

### Mint Smart ASA NFT

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

```shell
python3 smart_asa.py destroy 2991 KAVHOSWPO3XLBL5Q7FFOTPHAIRAT6DRDXUYGSLQOAEOPRSAXJKKPMHWLLQ

 --- Destroying Smart ASA 2991...
 --- Smart ASA 2991 destroyed!
```

## ABI Interface

### Smart ASA App Create

### Smart ASA Opt-In

```json
{
  "name": "asset_app_optin",
  "args": [{"type": "asset"}],
  "returns": {"type": "void"}
}
```

### Smart ASA Close-Out

```json
{
  "name": "asset_app_closeout",
  "args": [{"type": "asset"}],
  "returns": {"type": "void"}
}
```

### Smart ASA Create Underlying ASA

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

### Smart ASA Freeze

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
