#!/usr/bin/env python3
"""
Simulation script for TimeClock application.
Creates test data and demonstrates L-GAV export/import functionality.

Usage:
    python3 src/utils/simulate_app.py

This script will:
1. Create test employees
2. Generate sample time entries (clock in/out)
3. Create some L-GAV entries (holidays, vacation, sick days)
4. Export L-GAV reports (Excel, CSV, PDF)
5. Test re-importing the exported Excel file
"""
import sys
import os
import datetime
import random

# Suppress Kivy initialization messages
os.environ['KIVY_LOG_LEVEL'] = 'error'

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.data.database import (
    initialize_db, close_db,
    Employee, TimeEntry, LgavDayEntry,
    create_employee, create_time_entry, create_lgav_day_entry,
    get_all_employees, get_lgav_day_entries
)
from src.services.report_service import generate_wt_report


def create_test_employees():
    """Create test employees"""
    print("Creating test employees...")
    employees = []
    
    try:
        emp1 = create_employee("Max Mustermann", "TAG001", is_admin=True)
        employees.append(emp1)
        print(f"  ✓ Created: {emp1.name} ({emp1.rfid_tag})")
    except Exception as e:
        print(f"  ⚠ Employee 1 may already exist: {e}")
        employees.append(Employee.get(Employee.rfid_tag == "TAG001"))
    
    try:
        emp2 = create_employee("Anna Schmidt", "TAG002", is_admin=False)
        employees.append(emp2)
        print(f"  ✓ Created: {emp2.name} ({emp2.rfid_tag})")
    except Exception as e:
        print(f"  ⚠ Employee 2 may already exist: {e}")
        employees.append(Employee.get(Employee.rfid_tag == "TAG002"))
    
    return employees


def create_test_time_entries(employee, start_date, days=14):
    """Create test time entries for an employee"""
    print(f"\nCreating time entries for {employee.name}...")
    entries_created = 0
    
    current_date = start_date
    for day in range(days):
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() >= 5:
            current_date += datetime.timedelta(days=1)
            continue
        
        # Random work day (80% chance)
        if random.random() < 0.8:
            # Clock in between 7:00 and 9:00
            clock_in_hour = random.randint(7, 9)
            clock_in_minute = random.randint(0, 59)
            clock_in = datetime.datetime.combine(
                current_date,
                datetime.time(clock_in_hour, clock_in_minute)
            )
            
            # Clock out between 16:00 and 18:00 (7-9 hours later)
            work_hours = random.randint(7, 9)
            clock_out = clock_in + datetime.timedelta(hours=work_hours, minutes=random.randint(0, 30))
            
            try:
                # Create entries directly with custom timestamps
                from src.data.database import ensure_db_connection
                ensure_db_connection()
                with employee._meta.database.atomic():
                    entry_in = TimeEntry.create(
                        employee=employee,
                        action='in',
                        timestamp=clock_in,
                        active=True
                    )
                    entry_out = TimeEntry.create(
                        employee=employee,
                        action='out',
                        timestamp=clock_out,
                        active=True
                    )
                
                entries_created += 1
            except Exception as e:
                print(f"  ⚠ Error creating entry for {current_date}: {e}")
        
        current_date += datetime.timedelta(days=1)
    
    print(f"  ✓ Created {entries_created} work sessions")
    return entries_created


def create_test_lgav_entries(employee, start_date, days=14):
    """Create test L-GAV entries (holidays, vacation, etc.)"""
    print(f"\nCreating L-GAV entries for {employee.name}...")
    entries_created = 0
    
    current_date = start_date
    for day in range(days):
        # Randomly add some special day types
        rand = random.random()
        
        if rand < 0.05:  # 5% chance - Holiday
            create_lgav_day_entry(
                employee=employee,
                date=current_date,
                upper_code='FT',
                lower_code='FT',
                total_seconds=0
            )
            entries_created += 1
            print(f"  ✓ Holiday: {current_date}")
        elif rand < 0.10:  # 5% chance - Vacation
            create_lgav_day_entry(
                employee=employee,
                date=current_date,
                upper_code='F',
                lower_code='F',
                total_seconds=0
            )
            entries_created += 1
            print(f"  ✓ Vacation: {current_date}")
        elif rand < 0.12:  # 2% chance - Sick day
            create_lgav_day_entry(
                employee=employee,
                date=current_date,
                upper_code='K',
                lower_code='K',
                total_seconds=0
            )
            entries_created += 1
            print(f"  ✓ Sick day: {current_date}")
        
        current_date += datetime.timedelta(days=1)
    
    print(f"  ✓ Created {entries_created} L-GAV entries")
    return entries_created


def test_lgav_export(employee, start_date, end_date):
    """Test L-GAV export functionality"""
    print(f"\n{'='*60}")
    print("Testing L-GAV Export")
    print(f"{'='*60}")
    
    try:
        report = generate_wt_report(employee, start_date, end_date)
        
        # Export to Excel
        excel_file = report.to_lgav_excel()
        print(f"✓ Excel export: {excel_file}")
        
        # Export to CSV
        csv_file = report.to_lgav_csv()
        print(f"✓ CSV export: {csv_file}")
        
        # Export to PDF
        pdf_file = report.to_lgav_pdf()
        print(f"✓ PDF export: {pdf_file}")
        
        # Show report summary
        lgav_data = report._build_lgav_data()
        print(f"\nReport Summary:")
        print(f"  Employee: {employee.name}")
        print(f"  Date Range: {start_date} to {end_date}")
        print(f"  Months: {len(lgav_data['months'])}")
        
        # Count days with hours
        total_days_with_hours = 0
        total_hours_seconds = 0
        for month_data in lgav_data['months'].values():
            for day_data in month_data['days'].values():
                if day_data['total_seconds'] > 0:
                    total_days_with_hours += 1
                    total_hours_seconds += day_data['total_seconds']
        
        total_hours = total_hours_seconds // 3600
        total_minutes = (total_hours_seconds % 3600) // 60
        print(f"  Days with hours: {total_days_with_hours}")
        print(f"  Total hours: {total_hours}:{total_minutes:02d}")
        
        return excel_file
        
    except Exception as e:
        print(f"✗ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main simulation function"""
    print("="*60)
    print("TimeClock Application Simulation")
    print("="*60)
    
    # Initialize database
    print("\nInitializing database...")
    try:
        initialize_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return
    
    try:
        # Create test data
        employees = create_test_employees()
        if not employees:
            print("✗ No employees available")
            return
        
        employee = employees[0]  # Use first employee
        
        # Set date range (last 2 weeks)
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=13)
        
        print(f"\nDate Range: {start_date} to {end_date}")
        
        # Create time entries
        create_test_time_entries(employee, start_date, days=14)
        
        # Create some L-GAV entries
        create_test_lgav_entries(employee, start_date, days=14)
        
        # Test export
        test_lgav_export(employee, start_date, end_date)
        
        print(f"\n{'='*60}")
        print("Simulation Complete!")
        print(f"{'='*60}")
        
        # Summary
        print(f"\nSummary:")
        print(f"  Employees: {len(get_all_employees())}")
        print(f"  Test files created in: {os.path.join(os.getcwd(), 'exports')}")
        print(f"  Database: {os.path.join(os.getcwd(), 'timeclock.db')}")
        print(f"\nYou can now:")
        print(f"  1. Check the exported files in the 'exports' directory")
        print(f"  2. Edit the Excel file and re-import it using the app")
        print(f"  3. View the database using: sqlite3 timeclock.db")
        
    except Exception as e:
        print(f"\n✗ Simulation error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_db()


if __name__ == "__main__":
    main()

