#!/usr/bin/env python3
"""
Change an employee's name.

Usage:
    python change_employee_name.py [--name OLD_NAME] [--tag TAG] [--new-name NEW_NAME] [--all]
    
Examples:
    python change_employee_name.py --name "John Doe" --new-name "John Smith"
    python change_employee_name.py --tag "ABCD1234" --new-name "Jane Doe"
    python change_employee_name.py --all  # Interactive selection
"""
import argparse
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.database import (
    Employee, initialize_db, ensure_db_connection,
    get_employee_by_tag, get_all_employees, close_db, db
)


def main():
    parser = argparse.ArgumentParser(
        description="Change an employee's name",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --name "John Doe" --new-name "John Smith"
  %(prog)s --tag "ABCD1234" --new-name "Jane Doe"
  %(prog)s --all
        """
    )
    parser.add_argument(
        '--name', '-n',
        help='Current employee name (partial match supported)'
    )
    parser.add_argument(
        '--tag', '-t',
        help='Employee RFID tag'
    )
    parser.add_argument(
        '--new-name', '-N',
        help='New employee name'
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
                print(f"  {i}. {emp.name} ({emp.rfid_tag})")
            
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
        
        # Get new name
        new_name = args.new_name
        if not new_name:
            # Prompt for new name if not provided
            print(f"\n{'='*80}")
            print(f"Current employee information:")
            print(f"  Name:     {employee.name}")
            print(f"  RFID Tag: {employee.rfid_tag}")
            print(f"  Admin:    {'Yes' if employee.is_admin else 'No'}")
            print(f"  Active:   {'Yes' if employee.active else 'No'}")
            print(f"{'='*80}")
            
            new_name = input("\nEnter new name (or press Enter to cancel): ").strip()
            if not new_name:
                print("Cancelled.")
                sys.exit(0)
        
        # Validate new name
        if not new_name or len(new_name.strip()) == 0:
            print("ERROR: Employee name cannot be empty")
            sys.exit(1)
        
        if len(new_name) > 100:
            print("ERROR: Employee name cannot exceed 100 characters")
            sys.exit(1)
        
        # Check if name is the same
        if employee.name == new_name.strip():
            print(f"INFO: Name is already '{new_name}'. No change needed.")
            sys.exit(0)
        
        # Display change summary
        print(f"\n{'='*80}")
        print(f"Name change summary:")
        print(f"  Employee:    {employee.name} ({employee.rfid_tag})")
        print(f"  Old name:    {employee.name}")
        print(f"  New name:    {new_name.strip()}")
        print(f"{'='*80}")
        
        # Confirm change
        if not args.new_name:  # Only prompt if name wasn't provided via CLI
            response = input("\nProceed with name change? (yes/no): ").strip().lower()
            if response not in ('yes', 'y'):
                print("Cancelled.")
                sys.exit(0)
        
        # Update the name
        try:
            ensure_db_connection()
            with db.atomic():
                old_name = employee.name
                employee.name = new_name.strip()
                employee.save()
            
            print(f"\n✓ Name changed successfully!")
            print(f"  '{old_name}' → '{employee.name}'")
            print(f"  Employee RFID: {employee.rfid_tag}\n")
            
        except Exception as e:
            print(f"ERROR: Failed to update employee name: {e}")
            sys.exit(1)
        
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

