#!/usr/bin/env python3
"""
Delete a clock entry by ID and recalculate all following actions.

Usage:
    python delete_entry.py --id ENTRY_ID [--name NAME] [--tag TAG]
    
Examples:
    python delete_entry.py --id 431 --name "John Doe"
    python delete_entry.py --id 408 --tag "ABCD1234"
"""
import argparse
import os
import sys
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.database import (
    Employee, TimeEntry, initialize_db, ensure_db_connection,
    get_employee_by_tag, get_all_employees, close_db, soft_delete_time_entries, db
)


def format_timestamp(dt):
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def recalculate_actions(employee):
    """
    Recalculate actions for all active entries for an employee in chronological order.
    This ensures proper IN/OUT alternation after deletion.
    """
    ensure_db_connection()
    
    # Get all active entries for this employee, ordered chronologically
    all_entries = list(TimeEntry.select().where(
        TimeEntry.employee == employee,
        TimeEntry.active == True
    ).order_by(TimeEntry.timestamp.asc()))
    
    if not all_entries:
        print("  No active entries remaining to recalculate.")
        return 0
    
    # First, calculate all expected actions in memory (based on chronological order)
    expected_actions = []
    for i in range(len(all_entries)):
        if i == 0:
            # First entry should always be 'in'
            expected_actions.append('in')
        else:
            # Alternate based on previous expected action
            prev_expected = expected_actions[i-1]
            expected_actions.append('out' if prev_expected == 'in' else 'in')
    
    # Now update all entries that need changes
    updates_made = 0
    with db.atomic():
        for entry, expected_action in zip(all_entries, expected_actions):
            # Update if action is incorrect
            if entry.action != expected_action:
                TimeEntry.update(action=expected_action).where(TimeEntry.id == entry.id).execute()
                print(f"  Updated entry ID={entry.id} ({format_timestamp(entry.timestamp)}) "
                      f"from {entry.action.upper()} to {expected_action.upper()}")
                updates_made += 1
    
    if updates_made > 0:
        print(f"  ✓ Recalculated {updates_made} entry action(s)")
    else:
        print(f"  ✓ All {len(all_entries)} remaining entries already have correct actions")
    
    return updates_made


def main():
    parser = argparse.ArgumentParser(
        description="Delete a clock entry by ID and recalculate all following actions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --id 431 --name "John Doe"
  %(prog)s --id 408 --tag "ABCD1234"
        """
    )
    parser.add_argument(
        '--id', '-i',
        type=int,
        required=True,
        help='Entry ID to delete'
    )
    parser.add_argument(
        '--name', '-n',
        help='Employee name (for verification)'
    )
    parser.add_argument(
        '--tag', '-t',
        help='Employee RFID tag (for verification)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Skip employee verification (use with caution)'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    try:
        initialize_db()
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        sys.exit(1)
    
    try:
        ensure_db_connection()
        
        # Get the entry
        try:
            entry = TimeEntry.get_by_id(args.id)
        except TimeEntry.DoesNotExist:
            print(f"ERROR: Entry with ID {args.id} not found.")
            sys.exit(1)
        
        # Verify entry is active
        if not entry.active:
            print(f"ERROR: Entry ID {args.id} is already deleted (inactive).")
            sys.exit(1)
        
        # Get employee
        employee = entry.employee
        
        # Verify employee matches if provided
        if not args.force:
            if args.tag:
                if employee.rfid_tag.upper() != args.tag.upper():
                    print(f"ERROR: Entry ID {args.id} belongs to employee '{employee.name}' "
                          f"({employee.rfid_tag}), not '{args.tag}'")
                    print(f"       Use --force to delete anyway, or provide correct employee identifier.")
                    sys.exit(1)
            elif args.name:
                if args.name.lower() not in employee.name.lower():
                    print(f"ERROR: Entry ID {args.id} belongs to employee '{employee.name}' "
                          f"({employee.rfid_tag}), not '{args.name}'")
                    print(f"       Use --force to delete anyway, or provide correct employee identifier.")
                    sys.exit(1)
        
        # Display entry info
        print(f"\n{'='*80}")
        print(f"Entry to delete:")
        print(f"  ID:        {entry.id}")
        print(f"  Employee:  {employee.name} ({employee.rfid_tag})")
        print(f"  Timestamp: {format_timestamp(entry.timestamp)}")
        print(f"  Action:    {entry.action.upper()}")
        print(f"{'='*80}")
        
        # Confirm deletion
        if not args.force:
            response = input("\nDelete this entry? (yes/no): ").strip().lower()
            if response not in ('yes', 'y'):
                print("Cancelled.")
                sys.exit(0)
        
        # Soft delete the entry
        print(f"\nDeleting entry ID={entry.id}...")
        deleted_count = soft_delete_time_entries([entry.id])
        
        if deleted_count == 0:
            print("ERROR: Failed to delete entry.")
            sys.exit(1)
        
        print(f"✓ Entry ID={entry.id} deleted successfully.")
        
        # Recalculate actions for remaining entries
        print(f"\nRecalculating actions for remaining entries...")
        updates = recalculate_actions(employee)
        
        print(f"\n{'='*80}")
        print(f"✓ Deletion complete!")
        print(f"  Entry ID {args.id} has been soft-deleted")
        print(f"  {updates} subsequent entry action(s) updated")
        print(f"{'='*80}\n")
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        close_db()


if __name__ == '__main__':
    main()


