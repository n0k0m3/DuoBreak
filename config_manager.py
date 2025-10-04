#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Configuration and database management for DuoBreak."""

import json
import os
import shutil
import sys
from crypto_utils import derive_encryption_key, verify_encryption_key, encrypt_data, decrypt_data


class ConfigManager:
    """Manages DuoBreak configuration database."""
    
    CONFIG_VERSION = b"DBv1"
    
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.encryption_key = None
        self.config = {}
        
    def find_databases(self, directory="."):
        """Find all .duo database files in a directory."""
        duo_files = [f for f in os.listdir(directory) if f.endswith(".duo")]
        return duo_files
    
    def select_database_interactive(self):
        """Interactively select or create a database."""
        duo_files = self.find_databases()
        
        if duo_files:
            print("Duo databases found:")
            for i, file in enumerate(duo_files, 1):
                print(f"{i}. {file}")
            
            while True:
                try:
                    choice = int(input("Enter the number corresponding to the database you want to use: "))
                    if 1 <= choice <= len(duo_files):
                        self.db_path = duo_files[choice - 1]
                        break
                    else:
                        print("Invalid input. Please enter a valid number.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")
        else:
            print("No Duo databases found. Creating a new database.")
            db_name = input("Enter a name for the new database: ").strip()
            self.db_path = f"{db_name}.duo"
    
    def load_config(self, password, max_attempts=3):
        """Load and decrypt the configuration database."""
        attempts = 0
        
        while attempts < max_attempts:
            if os.path.exists(self.db_path):
                with open(self.db_path, "rb") as f:
                    version = f.read(4)
                    if version != self.CONFIG_VERSION:
                        raise ValueError("Unsupported configuration file version")
                    
                    salt = f.read(16)
                    encrypted_data = f.read()
                
                self.encryption_key = derive_encryption_key(password, salt)[1]
                
                if verify_encryption_key(self.encryption_key, password, salt):
                    try:
                        decrypted_data = decrypt_data(encrypted_data, self.encryption_key)
                        self.config = json.loads(decrypted_data)
                        return True
                    except (ValueError, json.JSONDecodeError) as e:
                        attempts += 1
                        if attempts < max_attempts:
                            print(f"Incorrect password or corrupted data. Attempt {attempts}/{max_attempts}")
                else:
                    attempts += 1
                    if attempts < max_attempts:
                        print(f"Incorrect password. Attempt {attempts}/{max_attempts}")
            else:
                # Create new database
                salt, self.encryption_key = derive_encryption_key(password)
                self.config = {"keys": {}}
                self.save_config(salt)
                return True
        
        raise Exception("Maximum password attempts reached")
    
    def save_config(self, salt=None):
        """Save and encrypt the configuration database."""
        if salt is None:
            # Read existing salt
            with open(self.db_path, "rb") as f:
                version = f.read(4)
                salt = f.read(16)
        
        # Prepare data to save
        data_to_save = json.dumps(self.config).encode("utf-8")
        encrypted_data = encrypt_data(data_to_save, self.encryption_key)
        
        # Write to temporary file first
        temp_file = self.db_path + ".tmp"
        with open(temp_file, "wb") as f:
            f.write(self.CONFIG_VERSION + salt + encrypted_data)
        
        # Replace original file
        shutil.move(temp_file, self.db_path)
    
    def change_password(self, new_password):
        """Change the database password."""
        salt, new_key = derive_encryption_key(new_password)
        
        # Re-encrypt with new key
        data_to_save = json.dumps(self.config).encode("utf-8")
        self.encryption_key = new_key
        self.save_config(salt)
    
    def add_key(self, key_name, code, host, response, pubkey, privkey):
        """Add a new Duo key to the configuration."""
        if "keys" not in self.config:
            self.config["keys"] = {}
        
        self.config["keys"][key_name] = {
            "code": code,
            "host": host,
            "response": response,
            "pubkey": pubkey,
            "privkey": privkey
        }
        self.save_config()
    
    def delete_key(self, key_name):
        """Delete a Duo key from the configuration."""
        if key_name in self.config.get("keys", {}):
            del self.config["keys"][key_name]
            self.save_config()
            return True
        return False
    
    def get_key(self, key_name):
        """Get a specific Duo key configuration."""
        return self.config.get("keys", {}).get(key_name)
    
    def list_keys(self):
        """List all configured Duo keys."""
        return list(self.config.get("keys", {}).keys())
    
    def get_hotp_counter(self, key_name):
        """Get the current HOTP counter for a key."""
        return self.config["keys"][key_name].get("hotp_counter", 0)
    
    def increment_hotp_counter(self, key_name):
        """Increment and return the HOTP counter for a key."""
        if "hotp_counter" not in self.config["keys"][key_name]:
            self.config["keys"][key_name]["hotp_counter"] = 0
        
        self.config["keys"][key_name]["hotp_counter"] += 1
        self.save_config()
        return self.config["keys"][key_name]["hotp_counter"]
    
    def log_hotp_code(self, key_name, code, timestamp):
        """Log a generated HOTP code."""
        if "hotp_log" not in self.config["keys"][key_name]:
            self.config["keys"][key_name]["hotp_log"] = []
        
        self.config["keys"][key_name]["hotp_log"].append(
            f"{timestamp} ({key_name}): {code}"
        )
        self.save_config()
    
    def get_recent_hotp_codes(self, key_name, count=10):
        """Get recent HOTP codes for a key."""
        hotp_log = self.config["keys"][key_name].get("hotp_log", [])
        return hotp_log[-count:]