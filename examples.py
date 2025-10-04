#!/usr/bin/env python3
"""
Example script showing how to use DuoBreak modules programmatically.
This demonstrates how to integrate DuoBreak into your own Python scripts.
"""

import base64
import datetime
import pyotp
from config_manager import ConfigManager
from duo_api import activate_duo, approve_push_notifications

def example_view_hotp_without_increment():
    """Example: View current HOTP without incrementing counter."""
    
    config = ConfigManager("work.duo")
    config.load_config("mypassword")
    
    key_name = "work"
    key_config = config.get_key(key_name)
    
    hotp_secret = base64.b32encode(
        key_config["response"]["hotp_secret"].encode("ascii")
    ).decode("ascii")
    hotp = pyotp.HOTP(hotp_secret)
    
    # Get current counter WITHOUT incrementing
    current_counter = config.get_hotp_counter(key_name)
    
    if current_counter == 0:
        print("No HOTP codes have been generated yet.")
        print("Run example_add_and_use_key() first to generate a code.")
        return
    
    # Generate code at current counter
    code = hotp.at(current_counter)
    
    print(f"Current HOTP code: {code}")
    print(f"Counter: {current_counter}")
    print(f"Note: Counter was NOT incremented")


def example_add_and_use_key():
    """Example: Add a key and generate HOTP code."""
    
    # Initialize config manager
    config = ConfigManager("example.duo")
    
    # Load or create database
    password = "mysecurepassword"
    config.load_config(password)
    
    # Example: Add a new key (you'd get these from QR code or activation)
    code = "ABC123XYZ"
    host = "api-e0724a16.duosecurity.com"
    
    print("Activating Duo key...")
    response, pubkey, privkey = activate_duo(code, host)
    
    key_name = "example_key"
    config.add_key(key_name, code, host, response, pubkey, privkey)
    print(f"Key '{key_name}' added successfully")
    
    # Generate HOTP code (increments counter)
    key_config = config.get_key(key_name)
    hotp_secret = base64.b32encode(
        key_config["response"]["hotp_secret"].encode("ascii")
    ).decode("ascii")
    hotp = pyotp.HOTP(hotp_secret)
    
    counter = config.increment_hotp_counter(key_name)
    code = hotp.at(counter)
    
    print(f"Generated HOTP Code: {code} (counter: {counter})")
    
    # Log the code
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    config.log_hotp_code(key_name, code, timestamp)


def example_auto_approve_push():
    """Example: Automatically approve push notifications."""
    
    config = ConfigManager("work.duo")
    config.load_config("mypassword")
    
    key_name = "work"
    key_config = config.get_key(key_name)
    
    if not key_config:
        print(f"Key '{key_name}' not found")
        return
    
    print("Waiting for push notification...")
    success, transaction = approve_push_notifications(
        key_config,
        key_config["privkey"],
        max_attempts=20,
        poll_interval=5
    )
    
    if success:
        print(f"Push approved! Transaction: {transaction['urgid']}")
    else:
        print("No push received or timeout")


def example_list_all_keys():
    """Example: List all configured keys with details."""
    
    config = ConfigManager("work.duo")
    config.load_config("mypassword")
    
    keys = config.list_keys()
    
    print(f"Found {len(keys)} key(s):")
    for key_name in keys:
        key_config = config.get_key(key_name)
        customer = key_config["response"].get("customer_name", "Unknown")
        hotp_counter = config.get_hotp_counter(key_name)
        
        print(f"\n  Key: {key_name}")
        print(f"  Customer: {customer}")
        print(f"  Host: {key_config['host']}")
        print(f"  HOTP Counter: {hotp_counter}")
        
        # Show recent codes
        recent = config.get_recent_hotp_codes(key_name, count=3)
        if recent:
            print(f"  Recent codes:")
            for code_entry in recent:
                print(f"    {code_entry}")


def example_batch_hotp_generation():
    """Example: Generate multiple HOTP codes in advance."""
    
    config = ConfigManager("work.duo")
    config.load_config("mypassword")
    
    key_name = "work"
    key_config = config.get_key(key_name)
    
    hotp_secret = base64.b32encode(
        key_config["response"]["hotp_secret"].encode("ascii")
    ).decode("ascii")
    hotp = pyotp.HOTP(hotp_secret)
    
    print(f"Generating 5 HOTP codes for '{key_name}':")
    
    for i in range(5):
        counter = config.increment_hotp_counter(key_name)
        code = hotp.at(counter)
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        config.log_hotp_code(key_name, code, timestamp)
        print(f"  Code {i+1}: {code} (counter: {counter})")


if __name__ == "__main__":
    print("DuoBreak Programmatic Usage Examples")
    print("=" * 50)
    
    # Uncomment the example you want to run:
    
    # example_add_and_use_key()
    # example_view_hotp_without_increment()
    # example_auto_approve_push()
    # example_list_all_keys()
    # example_batch_hotp_generation()
    
    print("\nEdit this script to uncomment and run specific examples.")