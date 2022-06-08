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

The state schema of the Smart Contract implementing a Smart ASA App has been designed to match 1-to-1 the params of an ASA. In addition, this reference implementation requires users to opt-in to the application and initialize a local state.

#### Global State

The global state of the Smart ASA App in this reference implementation is defined as follows:

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

The reference implementation introduces new parameters to a Smart ASA. In particular, the Smart ASA App controls one ASA at a time. Therefore the `smart_asa_id` is used to enforce checks on the current underlying ASA. Is is also used to initialize the local state of users when they opt-in to the Smart ASA. 

> ref. implementation fosters a Smart ASA App controlling one underlying ASA, and it is stored into the variable smart_asa_id. In this way the App can self verify that users are opted-in to the correct underlying ASA.

> ref. implementation introduces the global variables freeze. This parameters can be configured by the manager of the Smart ASA. If true, transfers of Smart ASA are not allowed. This powerful functionality provides a new feature that allows the global freeze of an asset without need to specify the freezed addresses manually.

> ref. implementation grants minting and burning permissions to the reserve address.

#### Local State

The local state of the Smart ASA App in this reference implementation is defined as follows:

**Integer Variables**

- `smart_asa_id`
- `frozen`


#### Self Validation

> param checks onCreate. The ref implementation checks that it is deployed with the following global and local state. Check the state schema size!

#### Smart Contract ABI's type check

> we rely type checks on the client side. We only enforce checking on the address lengths and the boolean values (0 or 1).

## Smart ASA Methods

### Smart ASA App Create

### Smart ASA App Opt-In

#### ABI Interface

```json
{
  "name": "asset_app_optin",
  "args": [{"type": "asset"}],
  "returns": {"type": "void"}
}
```

#### Description

### Smart ASA App Close-Out

#### ABI Interface

```json
{
  "name": "asset_app_closeout",
  "args": [{"type": "asset"}],
  "returns": {"type": "void"}
}
```

#### Description

### Smart ASA Creation

#### ABI Interface

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

#### Description

### Smart ASA Configuration

#### ABI Interface

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

#### Description

### Smart ASA Transfer

#### ABI Interface

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

#### ABI Interface

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

#### Description

### Smart ASA Account Freeze

#### ABI Interface

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

#### Description

### Smart ASA Destroy

#### ABI Interface

```json
{
  "name": "asset_destroy",
  "args": [
    {"type": "asset"}
  ],
  "returns": {"type": "void"}
}
```

#### Description

### Smart ASA Getters

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
