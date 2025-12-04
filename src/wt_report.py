"""
Working Time (WT) Report Generator
Generates detailed working time reports per employee for HR purposes.
"""
import datetime
import logging
from collections import deque
from typing import List, Dict, Optional, Tuple
from database import Employee, TimeEntry, ensure_db_connection

logger = logging.getLogger(__name__)


class WorkingTimeReport:
    """Generates working time reports for employees"""
    
    def __init__(self, employee: Employee, start_date: Optional[datetime.date] = None, 
                 end_date: Optional[datetime.date] = None):
        """
        Initialize a working time report for an employee.
        
        Args:
            employee: Employee to generate report for
            start_date: Start date for report (defaults to first entry date)
            end_date: End date for report (defaults to today)
        """
        self.employee = employee
        self.start_date = start_date
        self.end_date = end_date or datetime.date.today()
        self.daily_sessions = []  # List of daily work sessions
        self.total_hours = 0.0
        self.total_minutes = 0
        
    def generate(self) -> Dict:
        """
        Generate the working time report.
        
        Returns:
            Dictionary containing report data:
            {
                'employee': Employee object,
                'start_date': start_date,
                'end_date': end_date,
                'daily_sessions': List of daily session data,
                'total_hours': Total hours worked,
                'total_days': Number of days worked,
                'summary': Summary statistics
            }
        """
        ensure_db_connection()
        
        # Reset state to prevent duplicate accumulation on repeated calls
        self.daily_sessions = []
        self.total_hours = 0.0
        self.total_minutes = 0
        
        # Get all time entries for employee in date range
        entries = self._get_time_entries()
        
        if not entries:
            logger.info(f"No time entries found for {self.employee.name}")
            return self._empty_report()
        
        # If no start_date specified, use first entry date
        if not self.start_date:
            first_entry = entries[0]
            self.start_date = first_entry.timestamp.date()
        
        # Process entries into daily sessions
        self._process_entries(entries)
        
        # Calculate totals
        self._calculate_totals()
        
        return {
            'employee': self.employee,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'daily_sessions': self.daily_sessions,
            'total_hours': self.total_hours,
            'total_days': len(self.daily_sessions),
            'summary': self._generate_summary()
        }
    
    def _get_time_entries(self) -> List[TimeEntry]:
        """Get all time entries for the employee in the date range"""
        query = TimeEntry.select().where(
            TimeEntry.employee == self.employee,
            TimeEntry.active == True
        ).order_by(TimeEntry.timestamp.asc())
        
        # Filter by date range if specified
        if self.start_date:
            start_datetime = datetime.datetime.combine(self.start_date, datetime.time.min)
            query = query.where(TimeEntry.timestamp >= start_datetime)
        
        end_datetime = datetime.datetime.combine(self.end_date, datetime.time.max)
        query = query.where(TimeEntry.timestamp <= end_datetime)
        
        entries = list(query)
        
        # DEBUG: Log all fetched entries
        logger.debug(f"[WT DEBUG] Fetched {len(entries)} entries for {self.employee.name}")
        for e in entries:
            logger.debug(f"  ID={e.id} | {e.timestamp} | action={e.action} | active={e.active}")
        
        return entries
    
    def _process_entries(self, entries: List[TimeEntry]):
        """Process time entries into daily work sessions"""
        # Group entries by date
        entries_by_date = {}
        for entry in entries:
            date = entry.timestamp.date()
            if date not in entries_by_date:
                entries_by_date[date] = []
            entries_by_date[date].append(entry)
        
        # Process each day
        for date in sorted(entries_by_date.keys()):
            day_entries = entries_by_date[date]
            sessions = self._process_day_entries(day_entries)
            
            for session in sessions:
                self.daily_sessions.append({
                    'date': date,
                    'clock_in': session['clock_in'],
                    'clock_out': session['clock_out'],
                    'hours': session['hours'],
                    'minutes': session['minutes'],
                    'total_minutes': session['total_minutes'],
                    'formatted_time': session['formatted_time']
                })
    
    def _process_day_entries(self, entries: List[TimeEntry]) -> List[Dict]:
        """
        Process entries for a single day into work sessions.
        Handles multiple in/out pairs per day.
        
        Returns:
            List of work sessions for the day
        """
        sessions = []
        pending_ins = deque()
        
        date_str = entries[0].timestamp.date() if entries else "N/A"
        logger.debug(f"[WT DEBUG] Processing {len(entries)} entries for date {date_str}")
        
        for entry in entries:
            logger.debug(f"  -> Entry ID={entry.id} action={entry.action} ts={entry.timestamp}")
            
            if entry.action == 'in':
                pending_ins.append((entry.timestamp, entry.id))
                logger.debug(f"     Queued IN. Pending queue size: {len(pending_ins)}")
            elif entry.action == 'out':
                if not pending_ins:
                    logger.warning(f"Clock out without clock in for {self.employee.name} on {entry.timestamp.date()}")
                    continue
                clock_in_time, clock_in_id = pending_ins.popleft()
                duration = entry.timestamp - clock_in_time
                total_seconds = int(duration.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                logger.debug(f"     Paired: IN(id={clock_in_id}, {clock_in_time}) <-> OUT(id={entry.id}, {entry.timestamp}) = {hours}h{minutes}m")
                
                sessions.append({
                    'clock_in': clock_in_time,
                    'clock_out': entry.timestamp,
                    'hours': hours,
                    'minutes': minutes,
                    'total_minutes': total_seconds // 60,
                    'formatted_time': f"{hours:02d}:{minutes:02d}",
                    'clock_in_entry_id': clock_in_id,
                    'clock_out_entry_id': entry.id
                })
        
        if pending_ins:
            logger.info(f"{len(pending_ins)} open session(s) for {self.employee.name} remain without a clock-out")
        
        logger.debug(f"[WT DEBUG] Day {date_str} resulted in {len(sessions)} session(s)")
        return sessions
    
    def _calculate_totals(self):
        """Calculate total hours and minutes worked"""
        total_minutes = sum(session['total_minutes'] for session in self.daily_sessions)
        self.total_hours = total_minutes / 60.0
        self.total_minutes = total_minutes
    
    def _generate_summary(self) -> Dict:
        """Generate summary statistics"""
        if not self.daily_sessions:
            return {
                'total_hours': 0,
                'total_minutes': 0,
                'formatted_total': "00:00",
                'average_hours_per_day': 0,
                'days_worked': 0
            }
        
        days_worked = len(set(session['date'] for session in self.daily_sessions))
        avg_hours = self.total_hours / days_worked if days_worked > 0 else 0
        
        total_hours_int = int(self.total_hours)
        total_mins_int = int((self.total_hours - total_hours_int) * 60)
        
        return {
            'total_hours': self.total_hours,
            'total_minutes': self.total_minutes,
            'formatted_total': f"{total_hours_int:02d}:{total_mins_int:02d}",
            'average_hours_per_day': round(avg_hours, 2),
            'days_worked': days_worked
        }
    
    def _empty_report(self) -> Dict:
        """Return empty report structure"""
        return {
            'employee': self.employee,
            'start_date': self.start_date or datetime.date.today(),
            'end_date': self.end_date,
            'daily_sessions': [],
            'total_hours': 0.0,
            'total_days': 0,
            'summary': {
                'total_hours': 0,
                'total_minutes': 0,
                'formatted_total': "00:00",
                'average_hours_per_day': 0,
                'days_worked': 0
            }
        }
    
    def to_csv(
        self,
        filename: Optional[str] = None,
        export_root: Optional[str] = None
    ) -> str:
        """
        Export report to CSV file.
        
        Args:
            filename: Optional filename. If not provided, generates one.
            export_root: Optional directory where the file should be written.
        
        Returns:
            Path to the generated CSV file
        """
        import csv
        import os
        
        report = self.generate()
        
        if filename is None:
            # Generate filename: WT_Report_EmployeeName_YYYYMMDD_YYYYMMDD.csv
            start_str = report['start_date'].strftime('%Y%m%d')
            end_str = report['end_date'].strftime('%Y%m%d')
            safe_name = "".join(c for c in report['employee'].name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            root = export_root or os.path.join(os.getcwd(), 'exports')
            filename = os.path.join(root, f"WT_Report_{safe_name}_{start_str}_{end_str}.csv")
        
        # Ensure exports directory exists
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else 'exports', exist_ok=True)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Working Time Report'])
            writer.writerow(['Employee:', report['employee'].name])
            writer.writerow(['Employee ID:', report['employee'].rfid_tag])
            writer.writerow(['Period:', f"{report['start_date']} to {report['end_date']}"])
            writer.writerow([])
            
            # Daily sessions
            writer.writerow(['Date', 'Clock In', 'Clock Out', 'Hours Worked'])
            for session in report['daily_sessions']:
                writer.writerow([
                    session['date'].strftime('%Y-%m-%d'),
                    session['clock_in'].strftime('%H:%M:%S'),
                    session['clock_out'].strftime('%H:%M:%S'),
                    session['formatted_time']
                ])
            
            writer.writerow([])
            
            # Summary
            summary = report['summary']
            writer.writerow(['Summary'])
            writer.writerow(['Total Hours:', f"{summary['formatted_total']}"])
            writer.writerow(['Days Worked:', summary['days_worked']])
            writer.writerow(['Average Hours per Day:', f"{summary['average_hours_per_day']:.2f}"])
        
        logger.info(f"WT Report exported to {filename}")
        return filename
    
    def to_text(self) -> str:
        """
        Generate a human-readable text report.
        
        Returns:
            Formatted text report
        """
        report = self.generate()
        lines = []
        
        lines.append("=" * 15)
        lines.append("WORKING TIME REPORT")
        lines.append("=" * 15)
        lines.append(f"Name: {report['employee'].name}")
        lines.append("")
        
        if not report['daily_sessions']:
            lines.append("No time entries found for this period.")
            return "\n".join(lines)
        
        # Daily sessions
        lines.append("-" * 60)
        lines.append(f"{'Date':<12} {'Clock In':<12} {'Clock Out':<12} {'Hours':<10}")
        lines.append("-" * 60)
        
        for session in report['daily_sessions']:
            lines.append(
                f"{session['date'].strftime('%Y-%m-%d'):<12} "
                f"{session['clock_in'].strftime('%H:%M:%S'):<12} "
                f"{session['clock_out'].strftime('%H:%M:%S'):<12} "
                f"{session['formatted_time']:<10}"
            )
        
        lines.append("-" * 60)
        
        # Summary
        summary = report['summary']
        lines.append("")
        lines.append("SUMMARY")
        lines.append("-" * 60)
        lines.append(f"Total Hours Worked: {summary['formatted_total']}")
        lines.append(f"Days Worked: {summary['days_worked']}")
        lines.append(f"Average Hours per Day: {summary['average_hours_per_day']:.2f}")
        lines.append("=" * 60)
        
        return "\n".join(lines)


def generate_wt_report(employee: Employee, start_date: Optional[datetime.date] = None,
                      end_date: Optional[datetime.date] = None) -> WorkingTimeReport:
    """
    Convenience function to create and generate a WT report.
    
    Args:
        employee: Employee to generate report for
        start_date: Start date (optional)
        end_date: End date (optional, defaults to today)
    
    Returns:
        WorkingTimeReport object with generated report
    """
    report = WorkingTimeReport(employee, start_date, end_date)
    report.generate()
    return report

