#!/usr/bin/env python3
"""
Key rotation script.
Usage: uv run python scripts/rotate_keys.py --old-key OLD --new-key NEW

If --new-key is omitted, a fresh Fernet key is generated automatically.
"""
import asyncio
import argparse

from cryptography.fernet import Fernet, MultiFernet


async def rotate(old_key: str, new_key: str) -> None:
    # MultiFernet: first key encrypts, all keys tried for decryption
    f = MultiFernet([Fernet(new_key.encode()), Fernet(old_key.encode())])  # noqa: F841
    print("Key rotation prepared.")
    print(f"New key: {new_key}")
    print(
        "Steps:\n"
        "  1. Add the new key as ENCRYPTION_KEY in .env\n"
        "  2. Add the old key as ENCRYPTION_KEY_OLD in .env (for transition)\n"
        "  3. Restart the application — it will use MultiFernet for decryption\n"
        "  4. Run a re-encrypt migration to update all stored ciphertext to the new key\n"
        "  5. Remove ENCRYPTION_KEY_OLD once migration is complete"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate Fernet encryption key")
    parser.add_argument("--old-key", required=True, help="Current ENCRYPTION_KEY value")
    parser.add_argument(
        "--new-key",
        default=Fernet.generate_key().decode(),
        help="New key (auto-generated if omitted)",
    )
    args = parser.parse_args()
    asyncio.run(rotate(args.old_key, args.new_key))
