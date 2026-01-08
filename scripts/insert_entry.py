#!/usr/bin/env python3
"""
Helper script to insert a time-clock entry for an employee.

The action (in/out) is automatically determined based on the last entry for that employee.
You only need to provide the employee identifier and timestamp.

Usage:
    python scripts/insert_entry.py --employee "John Doe" --time "2024-01-15 14:30:00"
    python scripts/insert_entry.py --tag "ABCD1234" --time "2024-01-15 14:30:00"
    python scripts/insert_entry.py --employee "John Doe"  # Uses current time
"""

import argparse
import sys
import os
from datetime import datetime

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.database import (
    ensure_db_connection, close_db,
    get_employee_by_tag, get_all_employees,
    create_time_entry, _get_employee_lock
)
from src.data.database import TimeEntry, db


def format_timestamp(dt):
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(time_str):
    """Parse datetime string in various formats"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse datetime: {time_str}. Supported formats: YYYY-MM-DD HH:MM:SS, YYYY-MM-DD, DD.MM.YYYY HH:MM:SS, etc.")


def find_employee(employee_name=None, tag_id=None):
    """Find employee by name or tag"""
    ensure_db_connection()
    
    if tag_id:
        employee = get_employee_by_tag(tag_id.upper())
        if not employee:
            print(f"❌ No employee found with RFID tag: {tag_id}")
            return None
        return employee
    
    if employee_name:
        employees = list(get_all_employees(include_inactive=False))
        # Try exact match first
        for emp in employees:
            if emp.name.lower() == employee_name.lower():
                return emp
        
        # Try partial match
        matches = [emp for emp in employees if employee_name.lower() in emp.name.lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"❌ Multiple employees match '{employee_name}':")
            for emp in matches:
                print(f"   - {emp.name} ({emp.rfid_tag})")
            return None
        else:
            print(f"❌ No employee found with name: {employee_name}")
            return None
    
    return None


def insert_entry(employee, timestamp=None):
    """
    Insert a time entry for an employee with auto-determined action.
    
    Args:
        employee: Employee object
        timestamp: datetime object (defaults to now)
    """
    ensure_db_connection()
    
    if timestamp is None:
        timestamp = datetime.now()
    
    # Get last entry to show what action will be determined
    last_entry = TimeEntry.get_last_for_employee(employee)
    
    if last_entry:
        print(f"📋 Last entry: {format_timestamp(last_entry.timestamp)} - {last_entry.action.upper()}")
        if last_entry.action == 'out':
            expected_action = 'in'
        else:
            expected_action = 'out'
    else:
        print("📋 No previous entries found")
        expected_action = 'in'
    
    print(f"🔍 Expected action: {expected_action.upper()}")
    print(f"⏰ Timestamp: {format_timestamp(timestamp)}")
    print()
    
    try:
        # Use employee-level lock to prevent concurrent modifications
        employee_lock = _get_employee_lock(employee.id)
        
        with employee_lock:
            ensure_db_connection()
            
            # Atomically determine action and create entry with custom timestamp
            with db.atomic():
                # Get last entry within transaction to prevent race conditions
                last_entry = TimeEntry.get_last_for_employee(employee)
                
                # Determine action based on last entry
                if not last_entry or last_entry.action == 'out':
                    action = 'in'
                else:
                    action = 'out'
                
                # Create entry with custom timestamp
                entry = TimeEntry.create(
                    employee=employee,
                    action=action,
                    timestamp=timestamp,
                    active=True
                )
                db.commit()
            
            print(f"✅ Entry created successfully!")
            print(f"   Employee: {employee.name}")
            print(f"   Action: {action.upper()}")
            print(f"   Timestamp: {format_timestamp(entry.timestamp)}")
            print(f"   Entry ID: {entry.id}")
            
            return entry
        
    except Exception as e:
        print(f"❌ Error creating entry: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Insert a time-clock entry for an employee with auto-determined action',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Insert entry with current time
  %(prog)s --employee "John Doe"
  
  # Insert entry with specific time
  %(prog)s --employee "John Doe" --time "2024-01-15 14:30:00"
  
  # Insert entry using RFID tag
  %(prog)s --tag "ABCD1234" --time "2024-01-15 14:30:00"
  
  # Insert entry for today at specific time
  %(prog)s --employee "John Doe" --time "14:30:00"
        """
    )
    
    # Employee identification (mutually exclusive)
    employee_group = parser.add_mutually_exclusive_group(required=True)
    employee_group.add_argument(
        '--employee', '-e',
        type=str,
        help='Employee name (partial match supported)'
    )
    employee_group.add_argument(
        '--tag', '-t',
        type=str,
        help='Employee RFID tag'
    )
    
    # Timestamp (optional)
    parser.add_argument(
        '--time', '-T',
        type=str,
        help='Timestamp for entry (default: current time). Formats: YYYY-MM-DD HH:MM:SS, YYYY-MM-DD, DD.MM.YYYY HH:MM:SS, etc.'
    )
    
    args = parser.parse_args()
    
    # Find employee
    employee = find_employee(employee_name=args.employee, tag_id=args.tag)
    if not employee:
        sys.exit(1)
    
    print(f"👤 Employee: {employee.name} ({employee.rfid_tag})")
    print()
    
    # Parse timestamp if provided
    timestamp = None
    if args.time:
        try:
            timestamp = parse_datetime(args.time)
            # If only time provided (HH:MM:SS), use today's date
            if ' ' not in args.time and ':' in args.time:
                today = datetime.now().date()
                time_parts = args.time.split(':')
                if len(time_parts) >= 2:
                    timestamp = datetime.combine(today, datetime.strptime(args.time, "%H:%M:%S").time())
        except ValueError as e:
            print(f"❌ Invalid timestamp format: {e}")
            sys.exit(1)
    
    # Insert entry
    entry = insert_entry(employee, timestamp)
    
    if entry:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

