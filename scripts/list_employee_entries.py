#!/usr/bin/env python3
"""
List all clock entries for an employee.

Usage:
    python list_employee_entries.py [--name NAME] [--tag TAG] [--all]
    
Examples:
    python list_employee_entries.py --name "John Doe"
    python list_employee_entries.py --tag "ABCD1234"
    python list_employee_entries.py --all  # List all employees first, then select
"""
import argparse
import os
import sys
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.database import (
    Employee, TimeEntry, initialize_db, ensure_db_connection,
    get_employee_by_tag, get_all_employees, close_db
)


def format_timestamp(dt):
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def list_entries_for_employee(employee):
    """List all clock entries for a given employee"""
    ensure_db_connection()
    
    entries = TimeEntry.select().where(
        TimeEntry.employee == employee,
        TimeEntry.active == True
    ).order_by(TimeEntry.timestamp.desc())
    
    entries_list = list(entries)
    
    if not entries_list:
        print(f"\nNo clock entries found for {employee.name} ({employee.rfid_tag})")
        return
    
    print(f"\n{'='*80}")
    print(f"Clock Entries for: {employee.name} ({employee.rfid_tag})")
    print(f"Total entries: {len(entries_list)}")
    print(f"{'='*80}")
    print(f"{'ID':<6} {'Date/Time':<20} {'Action':<8} {'Status':<10}")
    print(f"{'-'*80}")
    
    for entry in entries_list:
        status = "ACTIVE" if entry.active else "INACTIVE"
        action_display = entry.action.upper()
        print(f"{entry.id:<6} {format_timestamp(entry.timestamp):<20} {action_display:<8} {status:<10}")
    
    print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="List all clock entries for an employee",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --name "John Doe"
  %(prog)s --tag "ABCD1234"
  %(prog)s --all
        """
    )
    parser.add_argument(
        '--name', '-n',
        help='Employee name (partial match supported)'
    )
    parser.add_argument(
        '--tag', '-t',
        help='Employee RFID tag'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='List all employees first, then interactively select one'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    try:
        initialize_db()
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        sys.exit(1)
    
    try:
        employee = None
        
        if args.tag:
            # Find by RFID tag
            employee = get_employee_by_tag(args.tag.upper())
            if not employee:
                print(f"ERROR: No employee found with RFID tag: {args.tag}")
                sys.exit(1)
        
        elif args.name:
            # Find by name (partial match)
            ensure_db_connection()
            employees = list(Employee.select().where(
                Employee.name.contains(args.name),
                Employee.active == True
            ))
            
            if not employees:
                print(f"ERROR: No employee found with name containing: {args.name}")
                sys.exit(1)
            elif len(employees) == 1:
                employee = employees[0]
            else:
                print(f"\nMultiple employees found matching '{args.name}':")
                for i, emp in enumerate(employees, 1):
                    print(f"  {i}. {emp.name} ({emp.rfid_tag})")
                print("\nPlease use --tag to specify the exact employee, or use --all to select interactively.")
                sys.exit(1)
        
        elif args.all:
            # List all employees and let user select
            employees = list(get_all_employees())
            if not employees:
                print("No employees found in database.")
                sys.exit(1)
            
            print("\nAvailable employees:")
            for i, emp in enumerate(employees, 1):
                entry_count = TimeEntry.select().where(
                    TimeEntry.employee == emp,
                    TimeEntry.active == True
                ).count()
                print(f"  {i}. {emp.name} ({emp.rfid_tag}) - {entry_count} entries")
            
            try:
                choice = input("\nEnter employee number: ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(employees):
                    employee = employees[idx]
                else:
                    print("ERROR: Invalid selection")
                    sys.exit(1)
            except (ValueError, KeyboardInterrupt):
                print("\nCancelled.")
                sys.exit(0)
        
        else:
            parser.print_help()
            sys.exit(1)
        
        # List entries for the selected employee
        list_entries_for_employee(employee)
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        close_db()


if __name__ == '__main__':
    main()


