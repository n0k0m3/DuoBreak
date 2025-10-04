# Usage Guide

This guide covers common usage patterns and all available commands for DuoBreak.

## Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `add` | Add new Duo key | `duobreak.py add --qr-code qr.png --key-name work` |
| `delete` | Delete a key | `duobreak.py delete work` |
| `list` | List all keys | `duobreak.py list --json` |
| `hotp` | Generate HOTP code | `duobreak.py hotp work [--view]` |
| `push` | Approve push notification | `duobreak.py push work` |
| `hotp-history` | Show code history | `duobreak.py hotp-history work --count 20` |
| `change-password` | Change database password | `duobreak.py change-password` |

## Command-Line Usage

### Adding Keys

**From QR code:**
```bash
./duobreak.py add \
  --qr-code duo_qr_code.png \
  --key-name work \
  --db-path work.duo \
  --password-file .password
```

**From activation code:**
```bash
./duobreak.py add \
  --activation-code ABC123XYZ \
  --host api-xxxxx.duosecurity.com \
  --key-name personal \
  --password-file .password
```

### Listing Keys

**Human-readable:**
```bash
./duobreak.py list --password-file .password
```

**JSON output:**
```bash
./duobreak.py list --password-file .password --json
```

### HOTP (One-Time Passwords)

**Generate new code (increments counter):**
```bash
./duobreak.py hotp work --password-file .password
```

**View current code without incrementing:**
```bash
./duobreak.py hotp work --view --password-file .password
```

**JSON output:**
```bash
./duobreak.py hotp work --password-file .password --json
```

### Push Notifications

**Auto-approve with defaults (10 attempts, 10 sec interval):**
```bash
./duobreak.py push work --password-file .password
```

**Custom polling:**
```bash
./duobreak.py push work \
  --max-attempts 20 \
  --poll-interval 5 \
  --password-file .password
```

**JSON output:**
```bash
./duobreak.py push work --password-file .password --json
```

### HOTP History

**Last 10 codes (default):**
```bash
./duobreak.py hotp-history work --password-file .password
```

**Last 20 codes:**
```bash
./duobreak.py hotp-history work --count 20 --password-file .password
```

**JSON output:**
```bash
./duobreak.py hotp-history work --password-file .password --json
```

### Deleting Keys

```bash
./duobreak.py delete work --password-file .password
```

### Changing Database Password

```bash
./duobreak.py change-password --db-path work.duo
# Will prompt for new password twice
```

## Scripting and Automation

### Extract HOTP Code as Variable

```bash
CODE=$(./duobreak.py hotp work --password-file .password --json | jq -r '.code')
echo "Your code: $CODE"
```

### Extract All Key Names

```bash
./duobreak.py list --password-file .password --json | jq -r '.keys[].name'
```

### Shell Function for Quick HOTP

```bash
# Add to .bashrc or .zshrc
duo() {
    local key="${1:-work}"
    duobreak.py hotp "$key" \
      --password-file ~/.duo/.password \
      --json | jq -r '.code'
}

# Usage
duo work        # Generate code for 'work' key
duo personal    # Generate code for 'personal' key
```

### Shell Function for HOTP View

```bash
# View current code without incrementing
duo-view() {
    local key="${1:-work}"
    duobreak.py hotp "$key" --view \
      --password-file ~/.duo/.password
}
```

### Auto-Approve Push Script

```bash
#!/bin/bash
# duo-auto-approve.sh

PASS_FILE="$HOME/.duo/.password"
DB_PATH="$HOME/.duo/work.duo"
KEY_NAME="work"

duobreak.py push "$KEY_NAME" \
  --db-path "$DB_PATH" \
  --password-file "$PASS_FILE" \
  --max-attempts 30 \
  --poll-interval 5
```

### Cron Job for Scheduled Auto-Approve

```bash
# Auto-approve push every 5 minutes
*/5 * * * * /path/to/duobreak.py push work --password-file ~/.duo/.password --max-attempts 1 --poll-interval 1

# Auto-approve during work hours only (9 AM - 5 PM, Mon-Fri)
0 9-17 * * 1-5 /path/to/duobreak.py push work --password-file ~/.duo/.password --max-attempts 6 --poll-interval 10
```

### VPN Login Integration

```bash
#!/bin/bash
# vpn-login.sh

USERNAME="user@company.com"
PASSWORD="$(pass show vpn/password)"
DUO_CODE="$(duobreak.py hotp vpn --password-file ~/.duo/.password --json | jq -r '.code')"

vpn-connect --user "$USERNAME" --pass "$PASSWORD" --2fa "$DUO_CODE"
```

### Password Manager Integration

**Using `pass` (password-store):**
```bash
# Store password in pass
pass insert duo/work

# Use with duobreak
pass show duo/work | duobreak.py hotp work
```

**Using password file from pass:**
```bash
pass show duo/work > /tmp/.duo_pass
chmod 600 /tmp/.duo_pass
duobreak.py hotp work --password-file /tmp/.duo_pass
rm /tmp/.duo_pass
```

## Password Input Methods

DuoBreak supports multiple ways to provide passwords (in priority order):

### 1. Password File (Recommended)

```bash
echo "your_password" > .password
chmod 600 .password
duobreak.py hotp work --password-file .password
```

### 2. Stdin Piping

```bash
echo "your_password" | duobreak.py hotp work
```

### 3. Interactive Prompt

```bash
duobreak.py hotp work
# Will prompt: Enter password for work.duo:
```

### 4. Command-line Argument (Not Recommended)

```bash
duobreak.py hotp work --password "your_password"
# Warning: Visible in process list and shell history
```

## Common Workflows

### Initial Setup Workflow

```bash
# 1. Create password file
echo "secure_password" > .password
chmod 600 .password

# 2. Add first key from QR code
duobreak.py add \
  --qr-code duo_qr.png \
  --key-name work \
  --db-path work.duo \
  --password-file .password

# 3. Test with HOTP
duobreak.py hotp work --password-file .password

# 4. Test push notification
duobreak.py push work --password-file .password
```

### Daily Usage Workflow

```bash
# Generate HOTP when needed
duobreak.py hotp work --password-file .password

# Or view current without incrementing
duobreak.py hotp work --view --password-file .password

# Auto-approve push when triggered
duobreak.py push work --password-file .password
```

### Multi-Key Management

```bash
# Add multiple keys
duobreak.py add --qr-code work_qr.png --key-name work --password-file .password
duobreak.py add --qr-code personal_qr.png --key-name personal --password-file .password

# List all keys
duobreak.py list --password-file .password

# Use specific key
duobreak.py hotp work --password-file .password
duobreak.py hotp personal --password-file .password

# Delete unused key
duobreak.py delete oldkey --password-file .password
```

### Database Migration

```bash
# Export keys from old database (v1.x compatible)
duobreak.py list --db-path old.duo --password-file .old_pass --json > keys_backup.json

# Create new database with new password
echo "new_password" > .new_pass
chmod 600 .new_pass

# Re-add keys to new database (requires original activation codes or QR codes)
# Note: Counters will reset, you'll need to sync HOTP codes
```

## Troubleshooting

### Common Issues

**Error: "No .duo files found"**
```bash
# Solution: Specify path explicitly
duobreak.py list --db-path /path/to/database.duo
```

**Error: "Key not found"**
```bash
# Solution: List available keys
duobreak.py list --password-file .password
```

**HOTP codes not accepted**
```bash
# Solution: Check counter sync
duobreak.py hotp-history work --password-file .password

# If out of sync, generate codes until server accepts one
duobreak.py hotp work --password-file .password
# Copy and try
# Repeat until accepted
```

**Push notification not working**
```bash
# Solution: Increase max attempts and check interval
duobreak.py push work \
  --max-attempts 30 \
  --poll-interval 5 \
  --password-file .password
```

**View shows "No HOTP codes generated yet"**
```bash
# Solution: Generate first code without --view flag
duobreak.py hotp work --password-file .password

# Then view works
duobreak.py hotp work --view --password-file .password
```

### Debug Mode

Add verbose output by checking the tool results:

```bash
# Use --json to see detailed output
duobreak.py hotp work --password-file .password --json

# Example output:
# {
#   "status": "success",
#   "code": "123456",
#   "counter": 5,
#   "action": "generated"
# }
```

### Getting Help

```bash
# General help
duobreak.py --help

# Command-specific help
duobreak.py add --help
duobreak.py hotp --help
duobreak.py push --help
duobreak.py list --help
duobreak.py delete --help
duobreak.py hotp-history --help
duobreak.py change-password --help
```

## Advanced Usage

See [examples.py](../examples.py) for programmatic usage of DuoBreak modules in your own Python scripts.