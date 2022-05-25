import base64
from sandbox import Sandbox
from algosdk.kmd import KMDClient
from algosdk.v2client import algod

ALGOD_ADDRESS = "http://localhost:4001"
ALGOD_TOKEN = "a" * 64
KMD_ADDRESS = "http://localhost:4002"
KMD_TOKEN = ALGOD_TOKEN

INITIAL_FUNDS = 10_000_000

algod_client = algod.AlgodClient(algod_token=ALGOD_TOKEN, algod_address=ALGOD_ADDRESS)
kmd_client = KMDClient(kmd_token=KMD_TOKEN, kmd_address=KMD_ADDRESS)

def compile_program(source_code):
    compile_response = algod_client.compile(source_code)
    return base64.b64decode(compile_response["result"])

def deploy():
    creator_account = Sandbox.create(funds_amount=INITIAL_FUNDS)

if __name__ == "__main__":
    deploy()