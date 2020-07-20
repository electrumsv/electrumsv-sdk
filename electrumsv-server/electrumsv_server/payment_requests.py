from typing import Sequence

from bitcoinx import bip32_key_from_string, BIP32PublicKey, PublicKey

from .constants import XPUB_TEST


XPUB_INDEX = 0
XPUB_OBJ = bip32_key_from_string(XPUB_TEST)

def derive_pubkey(xpub: BIP32PublicKey, sequence: Sequence[int]) -> PublicKey:
    pubkey = xpub
    for n in sequence:
        pubkey = pubkey.child_safe(n)
    return pubkey

def get_next_script() -> bytes:
    global XPUB_INDEX
    derivation = (0, XPUB_INDEX)
    XPUB_INDEX += 1

    pubkey = derive_pubkey(XPUB_OBJ, derivation)
    return pubkey.P2PKH_script().to_bytes()

