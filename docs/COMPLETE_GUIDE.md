# DuoBreak - Complete Guide

This guide provides comprehensive documentation for DuoBreak's features, architecture, and advanced usage.

For basic usage examples, see [USAGE.md](USAGE.md).  
For quick command reference, see [QUICK_REFERENCE.md](QUICK_REFERENCE.md).

## Table of Contents

- [Module Documentation](#module-documentation)
- [Database Format](#database-format)
- [Password Management](#password-management)
- [Security Considerations](#security-considerations)
- [Debugging](#debugging)
- [Programmatic Usage](#programmatic-usage)

## Module Documentation

DuoBreak is split into four main modules for easier debugging and maintenance:

### crypto_utils.py

Handles all cryptographic operations with no dependencies on other modules.

**Functions:**
- `derive_encryption_key(password, salt=None)` - PBKDF2 key derivation (100,000 iterations)
- `verify_encryption_key(key, password, salt)` - Verify password matches derived key
- `encrypt_data(data, key)` - AES-CBC encryption with random IV
- `decrypt_data(encrypted_data, key)` - AES-CBC decryption

**When to debug:** Password issues, encryption errors, database corruption

### duo_api.py

Handles all Duo API communication.

**Functions:**
- `generate_rsa_keypair()` - Generate 2048-bit RSA keys for activation
- `activate_duo(code, host)` - Activate Duo account, returns (response, pubkey, privkey)
- `parse_qr_code(file_path)` - Extract activation code and host from QR image
- `get_transactions(key_config, privkey_pem)` - Fetch pending push notifications
- `reply_transaction(transaction_id, answer, key_config, privkey_pem)` - Approve/deny push
- `approve_push_notifications(...)` - Poll and auto-approve with retry logic

**When to debug:** API errors, activation failures, push notification issues

### config_manager.py

Manages database file operations and key storage.

**Class: ConfigManager**
- `__init__(db_path=None)` - Initialize with database path
- `load_config(password, max_attempts=3)` - Load and decrypt database
- `save_config(salt=None)` - Encrypt and save database
- `add_key(key_name, code, host, response, pubkey, privkey)` - Store new key
- `delete_key(key_name)` - Remove key
- `get_key(key_name)` - Retrieve key configuration
- `list_keys()` - Get all key names
- `increment_hotp_counter(key_name)` - Increment and return counter
- `get_hotp_counter(key_name)` - Get current counter without incrementing
- `log_hotp_code(key_name, code, timestamp)` - Log generated code
- `get_recent_hotp_codes(key_name, count=10)` - Retrieve code history

**When to debug:** Database load/save issues, key storage problems, counter management

### duobreak.py

Main CLI application that coordinates all modules.

**Functions:**
- `main()` - Argument parsing and command routing
- `cmd_*()` - Command handlers (add, delete, list, hotp, push, etc.)
- `get_password()` - Multi-source password input (file, stdin, interactive)
- `interactive_mode()` - Legacy menu interface

**When to debug:** CLI argument issues, command flow, password input problems

## Database Format

DuoBreak uses encrypted `.duo` files with the following structure:

```
+-------------------+
| Version (4 bytes) |  "DBv1"
+-------------------+
| Salt (16 bytes)   |  For PBKDF2
+-------------------+
| Encrypted Data    |  AES-CBC encrypted JSON
+-------------------+
```

**Encrypted JSON structure:**
```json
{
  "keys": {
    "keyname": {
      "code": "activation_code",
      "host": "api-xxxxx.duosecurity.com",
      "response": {
        "pkey": "...",
        "akey": "...",
        "hotp_secret": "...",
        "customer_name": "..."
      },
      "pubkey": "-----BEGIN PUBLIC KEY-----...",
      "privkey": "-----BEGIN PRIVATE KEY-----...",
      "hotp_counter": 5,
      "hotp_log": [
        "2025-01-15 10:30:00 (keyname): 123456",
        "2025-01-15 14:20:00 (keyname): 789012"
      ]
    }
  }
}
```

**Encryption details:**
- Algorithm: AES-256-CBC
- Key derivation: PBKDF2-HMAC-SHA256
- Iterations: 100,000
- IV: Random per encryption

## Password Management

### Priority Order

DuoBreak accepts passwords in this priority:

1. **Password file** (`--password-file`)
2. **Command argument** (`--password`)
3. **Stdin pipe**
4. **Interactive prompt**

### Best Practices

**For automation (recommended):**
```bash
echo "secure_password" > .password
chmod 600 .password
duobreak.py hotp work --password-file .password
```

**For interactive use:**
```bash
duobreak.py hotp work
# Will prompt securely
```

**For one-off scripts:**
```bash
echo "password" | duobreak.py hotp work
```

**Never use (visible in process list):**
```bash
duobreak.py hotp work --password "password"  # BAD!
```

### Password File Security

```bash
# Create with restricted permissions
(umask 077 && echo "password" > .password)

# Verify permissions
ls -l .password
# Should show: -rw------- (600)

# Store in secure location
mkdir -p ~/.duo && chmod 700 ~/.duo
mv .password ~/.duo/
```

## Security Considerations

### Encryption

- All data encrypted with AES-256-CBC
- Keys derived using PBKDF2 (100,000 iterations)
- Random IV for each encryption
- Salt stored with encrypted data

### Memory Safety

- Encryption keys cleared on exit via `atexit`
- Passwords overwritten after use
- No passwords logged or stored in plaintext

### File Permissions

```bash
# Database files
chmod 600 *.duo

# Password files
chmod 600 .password

# Secure directory
mkdir -p ~/.duo
chmod 700 ~/.duo
```

### Network Security

- All API calls use HTTPS
- SSL verification enabled by default (`VERIFY_SSL = True`)
- Can be disabled for testing: Set `VERIFY_SSL = False` in `duo_api.py`

### Key Storage

- Private keys stored encrypted in database
- Public keys stored for signature verification
- HOTP secrets stored encrypted
- All sensitive data encrypted at rest

## Debugging

### Enable Debug Logging

Add to any module:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Individual Modules

**Crypto:**
```python
from crypto_utils import derive_encryption_key, encrypt_data, decrypt_data

salt, key = derive_encryption_key("test123")
encrypted = encrypt_data(b"secret", key)
decrypted = decrypt_data(encrypted, key)
assert decrypted == b"secret"
```

**Duo API:**
```python
from duo_api import activate_duo

response, pub, priv = activate_duo("CODE", "api-xxxxx.duosecurity.com")
print(response)
```

**Config Manager:**
```python
from config_manager import ConfigManager

config = ConfigManager("test.duo")
config.load_config("password")
print(config.list_keys())
```

### Inspect Database

```bash
# View structure
duobreak.py list --password-file .password --json | jq '.'

# Check specific key
duobreak.py list --password-file .password --json | jq '.keys.work'

# View HOTP counter
duobreak.py hotp-history work --password-file .password --json | jq '.'
```

### Add Debug Output to API Calls

In `duo_api.py`:
```python
def get_transactions(key_config, privkey_pem):
    # ... existing code ...
    
    # Add before request
    print(f"DEBUG: URL: {url}")
    print(f"DEBUG: Headers: {headers}")
    print(f"DEBUG: Params: {params_data}")
    
    r = requests.get(...)
    
    # Add after request
    print(f"DEBUG: Status: {r.status_code}")
    print(f"DEBUG: Response: {r.text}")
    
    return r.json()
```

### Common Debug Scenarios

**Password issues:**
```python
# Test password derivation
from crypto_utils import derive_encryption_key, verify_encryption_key

salt, key = derive_encryption_key("mypassword")
print(f"Salt: {salt.hex()}")
print(f"Key: {key.hex()}")
print(f"Valid: {verify_encryption_key(key, 'mypassword', salt)}")
```

**HOTP sync issues:**
```bash
# Check current counter
duobreak.py hotp-history work --password-file .password | tail -1

# View without incrementing
duobreak.py hotp work --view --password-file .password
```

**API communication:**
```python
# Test transaction fetching
from duo_api import get_transactions
from config_manager import ConfigManager

config = ConfigManager("work.duo")
config.load_config("password")
key_config = config.get_key("work")

transactions = get_transactions(key_config, key_config["privkey"])
print(transactions)
```

## Programmatic Usage

See `examples.py` for complete examples. Basic patterns:

### Generate HOTP

```python
from config_manager import ConfigManager
import base64
import pyotp

config = ConfigManager("work.duo")
config.load_config("password")

key_config = config.get_key("work")
hotp_secret = base64.b32encode(
    key_config["response"]["hotp_secret"].encode("ascii")
).decode("ascii")

hotp = pyotp.HOTP(hotp_secret)
counter = config.increment_hotp_counter("work")
code = hotp.at(counter)

print(f"Code: {code}")
```

### Auto-approve Push

```python
from config_manager import ConfigManager
from duo_api import approve_push_notifications

config = ConfigManager("work.duo")
config.load_config("password")

key_config = config.get_key("work")

success, transaction = approve_push_notifications(
    key_config,
    key_config["privkey"],
    max_attempts=20,
    poll_interval=5
)

if success:
    print(f"Approved: {transaction['urgid']}")
```

### Add Key Programmatically

```python
from config_manager import ConfigManager
from duo_api import activate_duo, parse_qr_code

# From QR code
code, host = parse_qr_code("duo_qr.png")

# Or from activation code
code = "ABC123XYZ"
host = "api-xxxxx.duosecurity.com"

response, pubkey, privkey = activate_duo(code, host)

config = ConfigManager("work.duo")
config.load_config("password")
config.add_key("mykey", code, host, response, pubkey, privkey)
```

## Advanced Topics

### Custom Database Location

```python
import os
from config_manager import ConfigManager

# Use environment variable
db_path = os.environ.get("DUO_DB_PATH", "~/.duo/work.duo")
db_path = os.path.expanduser(db_path)

config = ConfigManager(db_path)
```

### Multiple Databases

```python
# Work database
work_config = ConfigManager("~/.duo/work.duo")
work_config.load_config(work_password)

# Personal database
personal_config = ConfigManager("~/.duo/personal.duo")
personal_config.load_config(personal_password)

# Use separately
work_code = generate_hotp(work_config, "work_key")
personal_code = generate_hotp(personal_config, "personal_key")
```

### Batch Operations

```python
from config_manager import ConfigManager

config = ConfigManager("work.duo")
config.load_config("password")

# Generate multiple codes
for key_name in config.list_keys():
    key_config = config.get_key(key_name)
    # ... generate code for each key
```

### Error Handling

```python
from config_manager import ConfigManager

try:
    config = ConfigManager("work.duo")
    config.load_config("password")
except Exception as e:
    if "password" in str(e).lower():
        print("Incorrect password")
    elif "version" in str(e).lower():
        print("Unsupported database version")
    else:
        print(f"Error: {e}")
```

## Extending DuoBreak

### Adding New Commands

Edit `duobreak.py`:

```python
# 1. Add subparser
export_parser = subparsers.add_parser("export", help="Export keys")
export_parser.add_argument("--format", choices=["json", "csv"])

# 2. Add handler
def cmd_export(args, config_manager):
    keys = config_manager.list_keys()
    if args.format == "json":
        print(json.dumps({"keys": keys}))
    return 0

# 3. Route in main()
elif args.command == "export":
    return cmd_export(args, config_manager)
```

### Adding New Storage Backend

Create new storage module:

```python
# s3_storage.py
class S3ConfigManager:
    def load_config(self, password): ...
    def save_config(self, salt=None): ...
    # ... implement same interface as ConfigManager
```

Use in `duobreak.py`:
```python
if args.storage == "s3":
    config_manager = S3ConfigManager(args.s3_bucket)
else:
    config_manager = ConfigManager(args.db_path)
```

### Adding New Auth Methods

In `duo_api.py`:
```python
def generate_totp(key_config):
    """Generate TOTP code"""
    secret = key_config["response"]["totp_secret"]
    totp = pyotp.TOTP(secret)
    return totp.now()
```

In `duobreak.py`:
```python
totp_parser = subparsers.add_parser("totp", help="Generate TOTP")
# ... add command handler
```

## Troubleshooting

For common issues and solutions, see [USAGE.md](USAGE.md#troubleshooting).