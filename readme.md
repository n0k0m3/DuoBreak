# DuoBreak 2.0

A modular, CLI-friendly Duo authentication bypass tool with support for both interactive and non-interactive usage.

## Installation

```bash
git clone https://github.com/JesseNaser/DuoBreak.git
cd DuoBreak
pip install -r requirements.txt
chmod +x duobreak.py
```

## Quick Setup

Create a password file and add your first Duo key from a QR code:

```bash
echo "your_secure_password" > .password
chmod 600 .password

./duobreak.py add \
  --qr-code duo_qr_code.png \
  --key-name work \
  --db-path work.duo \
  --password-file .password
```

## Quick Usage

```bash
# Approve push notification
./duobreak.py push work --password-file .password

# Generate HOTP code (increments counter)
./duobreak.py hotp work --password-file .password

# View current code without incrementing
./duobreak.py hotp work --view --password-file .password

# List all configured keys
./duobreak.py list --password-file .password
```

## Interactive Mode

```bash
# Launch interactive menu
./duobreak.py --db-path work.duo
```

The interactive menu provides:
- Add/delete keys via QR code or activation code
- Generate HOTP codes
- Approve push notifications  
- Change database password
- View HOTP history

## Getting Help

```bash
# General help
./duobreak.py --help

# Command-specific help
./duobreak.py <command> --help
```

Examples:
```bash
./duobreak.py add --help
./duobreak.py hotp --help
./duobreak.py push --help
```

## Documentation

- **[Usage Examples](docs/USAGE.md)** - Command examples and common use cases
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet
- **[Complete Guide](docs/COMPLETE_GUIDE.md)** - Full documentation

## Security Best Practices

- Use password files with strict permissions (`chmod 600`)
- Never use `--password` flag (visible in process list)
- Store `.duo` databases in a secure location
- Use password managers for password file content

## Requirements

- Python 3.7+
- See `requirements.txt` for dependencies

## License

AGPL-3.0-or-later

For security updates, visit: [github.com/JesseNaser/DuoBreak](https://github.com/JesseNaser/DuoBreak)

---

**Disclaimer:** This tool is for educational and authorized testing purposes only. Ensure you have permission to use this tool on any Duo-protected systems.