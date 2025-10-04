#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Duo API interaction functions."""

from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from PIL import Image
import base64
import datetime
import email.utils
import requests
import urllib.parse

VERIFY_SSL = True


def generate_rsa_keypair():
    """Generate a 2048-bit RSA key pair."""
    key_pair = RSA.generate(2048)
    pubkey_data = key_pair.publickey().export_key("PEM").decode("ascii")
    privkey_data = key_pair.export_key("PEM").decode("ascii")
    return pubkey_data, privkey_data


def activate_duo(code, host):
    """Activate a Duo account using activation code and host."""
    url = f"https://{host}/push/v2/activation/{code}"

    headers = {
        "User-Agent": "DuoMobileApp/4.73.0.873.1 (arm64; iOS 18.1); Client: Foundation",
        "Accept": "*/*",
        "Accept-Language": "en-us",
        "Accept-Encoding": "gzip, deflate, br"
    }

    pubkey_data, privkey_data = generate_rsa_keypair()

    data = {
        "app_id": "com.duosecurity.DuoMobile",
        "app_version": "4.73.0.873.1",
        "ble_status": "allowed",
        "build_version": "24B5055e",
        "customer_protocol": "1",
        "device_name": "iPad",
        "jailbroken": "false",
        "language": "en",
        "manufacturer": "Apple",
        "model": "arm64",
        "notification_status": "not_determined",
        "passcode_status": "true",
        "pkpush": "rsa-sha512",
        "platform": "iOS",
        "pubkey": pubkey_data,
        "region": "US",
        "security_patch_level": "",
        "touchid_status": "true",
        "version": "18.1"
    }

    r = requests.post(url, headers=headers, data=data, verify=VERIFY_SSL)
    response = r.json()

    if "response" in response:
        return response["response"], pubkey_data, privkey_data
    else:
        raise Exception(f"Activation failed: {response}")


def parse_qr_code(file_path):
    """Parse a Duo QR code image and extract activation code and host."""
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
    except ImportError:
        raise ImportError("pyzbar is required for QR code parsing. Install it with: pip install pyzbar")
    
    img = Image.open(file_path)
    decoded_data = pyzbar_decode(img)
    
    if decoded_data:
        qr_data = decoded_data[0].data.decode()
        code, host = map(lambda x: x.strip("<>"), qr_data.split("-"))
        missing_padding = len(host) % 4
        if missing_padding:
            host += "=" * (4 - missing_padding)
        return code, base64.b64decode(host.encode("ascii")).decode("ascii")
    else:
        raise ValueError("Could not decode the QR code")


def generate_signature(method, path, timestamp, data, pkey, privkey_pem):
    """Generate a signature for Duo API requests."""
    pubkey = RSA.import_key(privkey_pem.encode("utf-8"))
    
    message = (timestamp + "\n" + method + "\n" + data["host"].lower() + "\n" +
               path + "\n" + urllib.parse.urlencode(data)).encode("ascii")
    h = SHA512.new(message)
    signature = pkcs1_15.new(pubkey).sign(h)
    auth = ("Basic " + base64.b64encode((pkey + ":" +
                                         base64.b64encode(signature).decode("ascii")).encode("ascii")).decode("ascii"))
    return auth


def get_transactions(key_config, privkey_pem):
    """Get pending Duo push transactions."""
    dt = datetime.datetime.now(datetime.timezone.utc)
    timestamp = email.utils.format_datetime(dt)
    path = "/push/v2/device/transactions"

    data = {
        "akey": key_config["response"]["akey"],
        "fips_status": "1",
        "hsm_status": "true",
        "pkpush": "rsa-sha512",
        "host": key_config["host"]
    }

    signature = generate_signature("GET", path, timestamp, data, 
                                   key_config["response"]["pkey"], privkey_pem)
    
    headers = {
        "Authorization": signature,
        "x-duo-date": timestamp,
        "host": key_config["host"]
    }

    # Remove 'host' from data for the params
    params_data = {k: v for k, v in data.items() if k != "host"}

    r = requests.get(f"https://{key_config['host']}{path}", 
                     params=params_data, headers=headers, verify=VERIFY_SSL)
    return r.json()


def reply_transaction(transaction_id, answer, key_config, privkey_pem):
    """Reply to a Duo push transaction."""
    dt = datetime.datetime.now(datetime.timezone.utc)
    timestamp = email.utils.format_datetime(dt)
    path = f"/push/v2/device/transactions/{transaction_id}"

    data = {
        "akey": key_config["response"]["akey"],
        "answer": answer,
        "fips_status": "1",
        "hsm_status": "true",
        "pkpush": "rsa-sha512",
        "host": key_config["host"]
    }

    signature = generate_signature("POST", path, timestamp, data,
                                   key_config["response"]["pkey"], privkey_pem)

    headers = {
        "Authorization": signature,
        "x-duo-date": timestamp,
        "host": key_config["host"],
        "txId": transaction_id
    }

    # Remove 'host' from data for the POST body
    post_data = {k: v for k, v in data.items() if k != "host"}

    r = requests.post(f"https://{key_config['host']}{path}", 
                      data=post_data, headers=headers, verify=VERIFY_SSL)
    return r.json()


def approve_push_notifications(key_config, privkey_pem, max_attempts=10, poll_interval=10):
    """Poll for and approve Duo push notifications."""
    failed_attempts = 0
    
    while failed_attempts < max_attempts:
        try:
            r = get_transactions(key_config, privkey_pem)
        except requests.exceptions.ConnectionError:
            print("Connection Error")
            failed_attempts += 1
            continue

        if "response" in r and "transactions" in r["response"]:
            transactions = r["response"]["transactions"]
            if transactions:
                for tx in transactions:
                    reply_transaction(tx["urgid"], "approve", key_config, privkey_pem)
                    return True, tx
            else:
                failed_attempts += 1
        else:
            print(f"Error fetching transactions. Server response: {r}")
            failed_attempts += 1

        if failed_attempts < max_attempts:
            import time
            time.sleep(poll_interval)
    
    return False, None