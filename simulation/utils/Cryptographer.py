"""
Utilities for key generation, encryption, and decryption with Fernet 128-bit AES key cryptography.
This file is named ``Cryptographer`` to not collide with the Python built-in module ``cryptography``.
"""
import base64
from cryptography.fernet import Fernet


class Key:
    """
    This class represents a Fernet cryptography key.

    Generate a new key with ``new()``, convert one into a savable string with ``to_str()``,
    or recover a ``Key`` from a saved string with ``from_str()``.
    """
    ENCODING: str = 'utf-8'

    def __init__(self, key: bytes):
        self.key = key

    @staticmethod
    def from_str(key_string: str):
        """
        Recover a ``Key`` from a ``key_string``.

        :param key_string: string that will be used to recover a Key
        :return: Key generated from ``key_string``
        """
        key_bytes: bytes = base64.b64decode(key_string.encode(Key.ENCODING))
        return Key(key_bytes)

    def to_str(self) -> str:
        """
        Encode a Key into a string.

        :return: a string representing this Key
        """
        return base64.b64encode(self.key).decode(Key.ENCODING)

    @staticmethod
    def new():
        """
        Generate a new Key

        :return: new Key
        """
        key: bytes = Fernet.generate_key()
        return Key(key)

    def __bytes__(self):
        return self.key


class Cryptographer:
    """
    Base class for cryptography-related methods
    """
    def __init__(self, key: Key):
        self.cipher = Fernet(bytes(key))


class Encryptor(Cryptographer):
    """
    Responsible for encrypting data
    """
    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt ``data`` and return the encrypted bytes.
        :param data: bytes to be encrypted
        :return: the encrypted bytes
        """
        return self.cipher.encrypt(data)


class Decryptor(Cryptographer):
    """
    Responsible for decrypting data
    """
    def decrypt(self, data: bytes) -> bytes:
        """
        Decrypt ``data`` and return the decrypted bytes.
        :param data: encrypted bytes to be decrypted
        :return: the decrypted bytes
        """
        return self.cipher.decrypt(data)
