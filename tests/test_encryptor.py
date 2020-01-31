"""Tests for Salus iT600 local mode encryption."""

import unittest

from pyit600 import encryptor


class TestStringMethods(unittest.TestCase):
    test_euid = '0123456789abcdef'
    test_plaintext = 'plain'
    test_ciphertext = b'\x1a\x84\x9d\xeffE\xbd\xa5d\x16+!\x9b2\x94\x85'

    def test_encryption(self):
        cryptor = encryptor.IT600Encryptor(self.test_euid)
        ciphertext = cryptor.encrypt(self.test_plaintext)

        self.assertEqual(self.test_ciphertext, ciphertext)

    def test_decryption(self):
        cryptor = encryptor.IT600Encryptor(self.test_euid)
        plaintext = cryptor.decrypt(self.test_ciphertext)

        self.assertEqual(self.test_plaintext, plaintext)

    def test_encryption_decryption_cycle(self):
        cryptor = encryptor.IT600Encryptor(self.test_euid)
        ciphertext = cryptor.encrypt(self.test_plaintext)
        plaintext = cryptor.decrypt(ciphertext)

        self.assertEqual(self.test_plaintext, plaintext)

    def test_key_case_insensitivity(self):
        ciphertext1 = encryptor.IT600Encryptor(self.test_euid.lower()).encrypt(self.test_plaintext)
        ciphertext2 = encryptor.IT600Encryptor(self.test_euid.upper()).encrypt(self.test_plaintext)

        self.assertEqual(ciphertext1, ciphertext2)


if __name__ == '__main__':
    unittest.main()
