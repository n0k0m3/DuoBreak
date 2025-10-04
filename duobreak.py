#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Version: 2.0.0
# For security updates, visit github.com/JesseNaser/DuoBreak

"""
DuoBreak - Duo authentication bypass tool
Refactored with CLI support and modular architecture.
"""

import argparse
import atexit
import base64
import datetime
import getpass
import json
import os
import pyotp
import sys

from config_manager import ConfigManager
from duo_api import (
    activate_duo, 
    parse_qr_code, 
    approve_push_notifications,
    get_transactions,
    reply_transaction
)


def get_password_from_stdin():
    """Read password from stdin if available."""
    if not sys.stdin.isatty():
        password = sys.stdin.readline().strip()
        if password:
            return password
    return None


def get_password_interactive(prompt="Enter password: ", confirm=False):
    """Get password interactively with optional confirmation."""
    password = getpass.getpass(prompt, stream=sys.stdout)
    if len(password) < 8:
        print("Password must be at least 8 characters long.")
        return get_password_interactive(prompt, confirm)
    
    if confirm:
        password_confirm = getpass.getpass("Confirm password: ", stream=sys.stdout)
        if password != password_confirm:
            print("Passwords do not match. Please try again.")
            return get_password_interactive(prompt, confirm)
    
    return password


def get_password(password_arg=None, password_file=None, allow_stdin=True, interactive_prompt="Enter password: ", confirm=False):
    """Get password from various sources in order of priority."""
    # 1. From password file
    if password_file:
        with open(password_file, 'r') as f:
            return f.read().strip()
    
    # 2. From command line argument (least secure, but useful for scripts)
    if password_arg:
        return password_arg
    
    # 3. From stdin pipe
    if allow_stdin:
        stdin_password = get_password_from_stdin()
        if stdin_password:
            return stdin_password
    
    # 4. Interactive prompt
    return get_password_interactive(interactive_prompt, confirm)


def cmd_add_key(args, config_manager):
    """Add a new Duo key."""
    if args.qr_code:
        code, host = parse_qr_code(args.qr_code)
        print(f"Parsed QR code: {code}, {host}")
    elif args.activation_code and args.host:
        code = args.activation_code
        host = args.host
    else:
        print("Error: Either --qr-code or both --activation-code and --host are required")
        return 1
    
    key_name = args.key_name
    if not key_name:
        if args.interactive:
            key_name = input("Enter a nickname for the new key: ").strip()
            if not key_name:
                print("Key name is required")
                return 1
        else:
            print("Error: --key-name is required in non-interactive mode")
            return 1
    
    # Check if key already exists
    if config_manager.get_key(key_name):
        print(f"Error: Key '{key_name}' already exists")
        return 1
    
    # Activate
    print(f"Activating Duo key...")
    response, pubkey, privkey = activate_duo(code, host)
    
    # Save
    config_manager.add_key(key_name, code, host, response, pubkey, privkey)
    print(f"Key '{key_name}' added successfully")
    
    if args.json:
        print(json.dumps({"status": "success", "key_name": key_name}))
    
    return 0


def cmd_delete_key(args, config_manager):
    """Delete a Duo key."""
    if config_manager.delete_key(args.key_name):
        print(f"Key '{args.key_name}' deleted successfully")
        if args.json:
            print(json.dumps({"status": "success", "key_name": args.key_name}))
        return 0
    else:
        print(f"Error: Key '{args.key_name}' not found")
        if args.json:
            print(json.dumps({"status": "error", "message": "Key not found"}))
        return 1


def cmd_list_keys(args, config_manager):
    """List all configured keys."""
    keys = config_manager.list_keys()
    
    if args.json:
        key_data = []
        for key_name in keys:
            key_config = config_manager.get_key(key_name)
            key_data.append({
                "name": key_name,
                "customer_name": key_config["response"].get("customer_name", ""),
                "host": key_config.get("host", "")
            })
        print(json.dumps({"keys": key_data}))
    else:
        if not keys:
            print("No keys configured")
        else:
            print("Configured keys:")
            for key_name in keys:
                key_config = config_manager.get_key(key_name)
                customer_name = key_config["response"].get("customer_name", "Unknown")
                print(f"  - {key_name} ({customer_name})")
    
    return 0


def cmd_auth_push(args, config_manager):
    """Approve Duo push notifications."""
    key_config = config_manager.get_key(args.key_name)
    if not key_config:
        print(f"Error: Key '{args.key_name}' not found")
        return 1
    
    print(f"Polling for push notifications for '{args.key_name}'...")
    success, tx = approve_push_notifications(
        key_config, 
        key_config["privkey"],
        max_attempts=args.max_attempts,
        poll_interval=args.poll_interval
    )
    
    if success:
        print(f"Push notification approved successfully")
        if args.json:
            print(json.dumps({"status": "success", "transaction": tx}))
        return 0
    else:
        print(f"No push notifications received or max attempts reached")
        if args.json:
            print(json.dumps({"status": "error", "message": "No transactions or timeout"}))
        return 1


def cmd_auth_hotp(args, config_manager):
    """Generate HOTP code."""
    key_config = config_manager.get_key(args.key_name)
    if not key_config:
        print(f"Error: Key '{args.key_name}' not found")
        return 1
    
    response = key_config["response"]
    hotp_secret = base64.b32encode(response["hotp_secret"].encode("ascii")).decode("ascii")
    hotp = pyotp.HOTP(hotp_secret)
    
    if args.view:
        # View mode: get current counter without incrementing
        counter = config_manager.get_hotp_counter(args.key_name)
        if counter == 0:
            print("Warning: No HOTP codes have been generated yet. Counter is at 0.")
            print("Use without --view flag to generate the first code.")
            return 1
        hotp_code = hotp.at(counter)
        action = "Current"
    else:
        # Generate mode: increment counter and generate new code
        counter = config_manager.increment_hotp_counter(args.key_name)
        hotp_code = hotp.at(counter)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        config_manager.log_hotp_code(args.key_name, hotp_code, timestamp)
        action = "Generated"
    
    if args.json:
        print(json.dumps({
            "status": "success",
            "code": hotp_code,
            "counter": counter,
            "action": action.lower()
        }))
    else:
        print(f"{action} HOTP code: {hotp_code} (counter: {counter})")
    
    return 0


def cmd_show_hotp_history(args, config_manager):
    """Show recent HOTP codes."""
    key_config = config_manager.get_key(args.key_name)
    if not key_config:
        print(f"Error: Key '{args.key_name}' not found")
        return 1
    
    recent_codes = config_manager.get_recent_hotp_codes(args.key_name, args.count)
    
    if args.json:
        print(json.dumps({"status": "success", "codes": recent_codes}))
    else:
        if not recent_codes:
            print(f"No HOTP history for '{args.key_name}'")
        else:
            print(f"Recent HOTP codes for '{args.key_name}':")
            for code_entry in recent_codes:
                print(f"  {code_entry}")
    
    return 0


def cmd_change_password(args, config_manager):
    """Change database password."""
    new_password = get_password(
        args.new_password,
        None,  # Don't use password file for new password
        allow_stdin=False,
        interactive_prompt="Enter new password: ",
        confirm=True
    )
    
    config_manager.change_password(new_password)
    print("Password changed successfully")
    
    if args.json:
        print(json.dumps({"status": "success"}))
    
    return 0


def interactive_mode(config_manager):
    """Run in interactive menu mode (legacy compatibility)."""
    def interactive_add_key():
        print("\n1. Add using QR Code")
        print("2. Add using Activation Code and Host")
        choice = input("Select method (1 or 2): ").strip()
        
        key_name = input("Enter a nickname for the new key: ").strip()
        if not key_name:
            print("Key name cannot be empty")
            return
        
        if config_manager.get_key(key_name):
            print(f"Error: Key '{key_name}' already exists")
            return
        
        if choice == "1":
            try:
                from pyzbar.pyzbar import decode as pyzbar_decode
            except ImportError:
                print("Error: pyzbar is required for QR code parsing")
                print("Install it with: pip install pyzbar")
                return
            
            qr_path = input("Enter QR code image path: ").strip()
            if not qr_path or not os.path.exists(qr_path):
                print("Invalid file path")
                return
            
            code, host = parse_qr_code(qr_path)
        elif choice == "2":
            code = input("Enter activation code: ").strip()
            host = input("Enter host (e.g., api-xxxxx.duosecurity.com): ").strip()
        else:
            print("Invalid choice")
            return
        
        print("Activating...")
        response, pubkey, privkey = activate_duo(code, host)
        config_manager.add_key(key_name, code, host, response, pubkey, privkey)
        print(f"Key '{key_name}' added successfully")
    
    def interactive_authenticate():
        key_name = input("Enter key name: ").strip()
        key_config = config_manager.get_key(key_name)
        
        if not key_config:
            print(f"Error: Key '{key_name}' not found")
            return
        
        print("\n1. Duo Push")
        print("2. HOTP")
        print("3. Show recent HOTP codes")
        choice = input("Select method (1, 2, or 3): ").strip()
        
        if choice == "1":
            print("Polling for push notifications...")
            success, tx = approve_push_notifications(key_config, key_config["privkey"])
            if success:
                print("Push approved successfully")
            else:
                print("No transactions or timeout")
        
        elif choice == "2":
            response = key_config["response"]
            hotp_secret = base64.b32encode(response["hotp_secret"].encode("ascii")).decode("ascii")
            hotp = pyotp.HOTP(hotp_secret)
            
            counter = config_manager.increment_hotp_counter(key_name)
            hotp_code = hotp.at(counter)
            
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            config_manager.log_hotp_code(key_name, hotp_code, timestamp)
            
            print(f"HOTP code: {hotp_code}")
        
        elif choice == "3":
            recent_codes = config_manager.get_recent_hotp_codes(key_name)
            if recent_codes:
                print(f"Recent HOTP codes for '{key_name}':")
                for code_entry in recent_codes:
                    print(f"  {code_entry}")
            else:
                print(f"No HOTP history for '{key_name}'")
    
    while True:
        print("\n=== DuoBreak Main Menu ===")
        print("1. Add a new key")
        print("2. Delete a key")
        print("3. List keys")
        print("4. Authenticate")
        print("5. Change password")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            interactive_add_key()
        elif choice == "2":
            key_name = input("Enter key name to delete: ").strip()
            if config_manager.delete_key(key_name):
                print(f"Key '{key_name}' deleted")
            else:
                print(f"Key '{key_name}' not found")
        elif choice == "3":
            keys = config_manager.list_keys()
            if keys:
                print("\nConfigured keys:")
                for key_name in keys:
                    key_config = config_manager.get_key(key_name)
                    customer_name = key_config["response"].get("customer_name", "Unknown")
                    print(f"  - {key_name} ({customer_name})")
            else:
                print("No keys configured")
        elif choice == "4":
            interactive_authenticate()
        elif choice == "5":
            new_password = get_password_interactive("Enter new password: ", confirm=True)
            config_manager.change_password(new_password)
            print("Password changed successfully")
        elif choice == "6":
            print("Exiting...")
            return 0
        else:
            print("Invalid choice")


def main():
    parser = argparse.ArgumentParser(
        description="DuoBreak - Duo authentication tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  duobreak.py --db-path work.duo

  # Add key from QR code
  echo "mypassword" | duobreak.py add --qr-code qr.png --key-name work

  # Add key with activation code
  duobreak.py add --activation-code ABC123 --host api-xxx.duosecurity.com --key-name personal --password-file .pass

  # List keys
  duobreak.py list --db-path ~/duo/work.duo

  # Generate HOTP code (increments counter)
  duobreak.py hotp work

  # View current HOTP code (without incrementing)
  duobreak.py hotp work --view

  # Approve push notification
  duobreak.py push work

  # Show HOTP history
  duobreak.py hotp-history work --count 20
        """
    )
    
    # Global options
    parser.add_argument("--db-path", help="Path to .duo database file (required for interactive mode)")
    parser.add_argument("--password", help="Database password (NOT RECOMMENDED - use stdin or --password-file instead)")
    parser.add_argument("--password-file", help="Path to file containing database password")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive prompts when needed")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add key command
    add_parser = subparsers.add_parser("add", help="Add a new Duo key")
    add_parser.add_argument("--key-name", help="Nickname for the key")
    add_parser.add_argument("--qr-code", help="Path to QR code image")
    add_parser.add_argument("--activation-code", help="Activation code")
    add_parser.add_argument("--host", help="Duo host (e.g., api-xxxxx.duosecurity.com)")
    
    # Delete key command
    delete_parser = subparsers.add_parser("delete", help="Delete a Duo key")
    delete_parser.add_argument("key_name", help="Name of the key to delete")
    
    # List keys command
    list_parser = subparsers.add_parser("list", help="List all configured keys")
    
    # Push authentication command
    push_parser = subparsers.add_parser("push", help="Approve Duo push notification")
    push_parser.add_argument("key_name", help="Name of the key to use")
    push_parser.add_argument("--max-attempts", type=int, default=10, help="Maximum polling attempts (default: 10)")
    push_parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between polls (default: 10)")
    
    # HOTP command
    hotp_parser = subparsers.add_parser("hotp", help="Generate HOTP code")
    hotp_parser.add_argument("key_name", help="Name of the key to use")
    hotp_parser.add_argument("--view", action="store_true", help="View current code without incrementing counter")
    
    # HOTP history command
    history_parser = subparsers.add_parser("hotp-history", help="Show recent HOTP codes")
    history_parser.add_argument("key_name", help="Name of the key")
    history_parser.add_argument("--count", type=int, default=10, help="Number of recent codes to show (default: 10)")
    
    # Change password command
    passwd_parser = subparsers.add_parser("change-password", help="Change database password")
    passwd_parser.add_argument("--new-password", help="New password (NOT RECOMMENDED - use interactive prompt instead)")
    
    args = parser.parse_args()
    
    # If no command specified, run interactive mode
    if not args.command:
        # Interactive mode - db-path is REQUIRED
        if not args.db_path:
            parser.error("--db-path is required for interactive mode\n\nExamples:\n  duobreak.py --db-path work.duo\n  duobreak.py --db-path /path/to/database.duo")
        
        config_manager = ConfigManager(args.db_path)
        
        # Get password
        if os.path.exists(config_manager.db_path):
            password = get_password(args.password, args.password_file, interactive_prompt="Enter password to unlock vault: ")
        else:
            password = get_password_interactive("Enter password to create new vault: ", confirm=True)
        
        config_manager.load_config(password)
        
        # Clean up password from memory
        def cleanup():
            config_manager.encryption_key = None
        atexit.register(cleanup)
        
        return interactive_mode(config_manager)
    
    # CLI mode - determine database path
    if args.db_path:
        db_path = args.db_path
    else:
        # Look for .duo files in current directory
        duo_files = [f for f in os.listdir(".") if f.endswith(".duo")]
        if len(duo_files) == 1:
            db_path = duo_files[0]
        elif len(duo_files) > 1:
            print(f"Error: Multiple .duo files found. Please specify --db-path")
            return 1
        else:
            print(f"Error: No .duo files found. Please specify --db-path or create a database first")
            return 1
    
    # Initialize config manager
    config_manager = ConfigManager(db_path)
    
    # Get password
    if os.path.exists(db_path):
        password = get_password(args.password, args.password_file, interactive_prompt=f"Enter password for {db_path}: ")
    else:
        password = get_password(args.password, args.password_file, interactive_prompt=f"Enter password to create {db_path}: ", confirm=True)
    
    try:
        config_manager.load_config(password)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    # Clean up password from memory
    def cleanup():
        config_manager.encryption_key = None
    atexit.register(cleanup)
    
    # Execute command
    if args.command == "add":
        return cmd_add_key(args, config_manager)
    elif args.command == "delete":
        return cmd_delete_key(args, config_manager)
    elif args.command == "list":
        return cmd_list_keys(args, config_manager)
    elif args.command == "push":
        return cmd_auth_push(args, config_manager)
    elif args.command == "hotp":
        return cmd_auth_hotp(args, config_manager)
    elif args.command == "hotp-history":
        return cmd_show_hotp_history(args, config_manager)
    elif args.command == "change-password":
        return cmd_change_password(args, config_manager)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())