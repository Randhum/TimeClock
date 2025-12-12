#!/usr/bin/env python3
"""
Database Migration Tool for TimeClock
Migrates an unencrypted SQLite database to SQLCipher encrypted format.

Usage:
    python migrate_db.py [--source timeclock.db] [--target timeclock_encrypted.db]
    
The encryption key will be read from TIMECLOCK_ENV_KEY environment variable.
"""
import argparse
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def main():
    parser = argparse.ArgumentParser(
        description="Migrate unencrypted TimeClock database to SQLCipher encrypted format"
    )
    parser.add_argument(
        '--source', '-s',
        default='timeclock.db',
        help='Path to unencrypted source database (default: timeclock.db)'
    )
    parser.add_argument(
        '--target', '-t', 
        default='timeclock_encrypted.db',
        help='Path for encrypted target database (default: timeclock_encrypted.db)'
    )
    parser.add_argument(
        '--key', '-k',
        help='Encryption key (if not set, uses TIMECLOCK_ENV_KEY env var)'
    )
    
    args = parser.parse_args()
    
    # Get passphrase
    passphrase = args.key or os.getenv('TIMECLOCK_ENV_KEY')
    if not passphrase:
        print("ERROR: No encryption key provided!")
        print("Set TIMECLOCK_ENV_KEY environment variable or use --key option")
        sys.exit(1)
    
    if len(passphrase) < 16:
        print("WARNING: Encryption key should be at least 16 characters for security")
    
    # Check source exists
    if not os.path.exists(args.source):
        print(f"ERROR: Source database not found: {args.source}")
        sys.exit(1)
    
    # Check target doesn't exist
    if os.path.exists(args.target):
        print(f"ERROR: Target database already exists: {args.target}")
        print("Remove it first or choose a different target path")
        sys.exit(1)
    
    print(f"Migrating: {args.source} -> {args.target}")
    print("Using SQLCipher AES-256 encryption...")
    
    try:
        from database import migrate_to_encrypted
        
        success = migrate_to_encrypted(
            passphrase=passphrase,
            source_db=args.source,
            target_db=args.target
        )
        
        if success:
            print("\n✓ Migration successful!")
            print(f"\nNext steps:")
            print(f"  1. Backup your original database: mv {args.source} {args.source}.backup")
            print(f"  2. Use the encrypted database: mv {args.target} {args.source}")
            print(f"  3. Ensure TIMECLOCK_ENV_KEY is set when running the app")
        else:
            print("\n✗ Migration failed!")
            sys.exit(1)
            
    except ImportError as e:
        print(f"\nERROR: Missing dependency: {e}")
        print("Install SQLCipher: pip install sqlcipher3-binary")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

