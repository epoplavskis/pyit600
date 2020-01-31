"""Encryptor for Salus iT600 local mode communication."""

import hashlib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class IT600Encryptor:
    iv = bytes([0x88, 0xa6, 0xb0, 0x79, 0x5d, 0x85, 0xdb, 0xfc, 0xe6, 0xe0, 0xb3, 0xe9, 0xa6, 0x29, 0x65, 0x4b])

    def __init__(self, euid: str):
        key: bytes = hashlib.md5(f"Salus-{euid.lower()}".encode("utf-8")).digest() + bytes([0] * 16)
        self.cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv), default_backend())

    def encrypt(self, plain: str) -> bytes:
        encryptor = self.cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data: bytes = padder.update(plain.encode("utf-8")) + padder.finalize()
        return encryptor.update(padded_data) + encryptor.finalize()

    def decrypt(self, cypher: bytes) -> str:
        decryptor = self.cipher.decryptor()
        padded_data: bytes = decryptor.update(cypher) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plain: bytes = unpadder.update(padded_data) + unpadder.finalize()
        return plain.decode("utf-8")
