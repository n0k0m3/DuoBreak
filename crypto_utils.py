#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cryptographic utilities for DuoBreak."""

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os


def derive_encryption_key(password, salt=None):
    """Derive an encryption key from a password using PBKDF2."""
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return salt, kdf.derive(password.encode("utf-8"))


def verify_encryption_key(key, password, salt):
    """Verify that a password matches the derived key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    try:
        kdf.verify(password.encode("utf-8"), key)
        return True
    except Exception:
        return False


def encrypt_data(data, key):
    """Encrypt data using AES-CBC."""
    cipher = AES.new(key, AES.MODE_CBC)
    return cipher.iv + cipher.encrypt(pad(data, AES.block_size))


def decrypt_data(encrypted_data, key):
    """Decrypt data using AES-CBC."""
    iv = encrypted_data[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted_data[AES.block_size:]), AES.block_size)