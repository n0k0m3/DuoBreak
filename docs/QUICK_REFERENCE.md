# DuoBreak - Quick Reference

Essential commands and options for DuoBreak. For detailed examples, see [USAGE.md](USAGE.md).

## Command Structure

```
duobreak.py [GLOBAL_OPTIONS] <command> [COMMAND_OPTIONS]
```

## Global Options

| Option | Description |
|--------|-------------|
| `--db-path PATH` | Path to .duo database (required for interactive mode) |
| `--password PASS` | Password (not recommended) |
| `--password-file FILE` | Path to password file (recommended) |
| `--json` | Output in JSON format |
| `--interactive` | Enable interactive prompts |

## Commands

### add - Add New Key
```bash
# From QR code
duobreak.py add --qr-code IMAGE --key-name NAME

# From activation code
duobreak.py add --activation-code CODE --host HOST --key-name NAME
```

### list - List Keys
```bash
duobreak.py list [--json]
```

### hotp - Generate HOTP Code
```bash
# Generate (increments counter)
duobreak.py hotp KEYNAME

# View (no increment)
duobreak.py hotp KEYNAME --view
```

### push - Approve Push Notification
```bash
duobreak.py push KEYNAME [--max-attempts N] [--poll-interval N]
```

### hotp-history - Show HOTP History
```bash
duobreak.py hotp-history KEYNAME [--count N]
```

### delete - Delete Key
```bash
duobreak.py delete KEYNAME
```

### change-password - Change Database Password
```bash
duobreak.py change-password
```

## Password Input Priority

1. Password file (`--password-file .password`)
2. Command argument (`--password "pass"`)
3. Stdin pipe (`echo "pass" | duobreak.py ...`)
4. Interactive prompt

## Common Workflows

**Setup:**
```bash
echo "password" > .password && chmod 600 .password
duobreak.py add --qr-code qr.png --key-name work --password-file .password
```

**Daily use:**
```bash
duobreak.py hotp work --password-file .password
duobreak.py push work --password-file .password
```

**Scripting:**
```bash
CODE=$(duobreak.py hotp work --password-file .password --json | jq -r '.code')
```

## File Permissions

```bash
chmod 600 *.duo
chmod 600 .password
```

## Getting Help

```bash
duobreak.py --help
duobreak.py <command> --help
```
