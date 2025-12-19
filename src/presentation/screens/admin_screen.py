"""
Admin screen for managing exports and administration.
"""
import os
import csv
import io
import sqlite3
import tempfile
import datetime
import logging
from kivy.uix.screenmanager import Screen
from kivy.app import App

from ...data.database import db, get_time_entries_for_export
from ...utils.export_utils import get_export_directory, write_file
from ...services.report_service import generate_all_employees_lgav_excel
from kivy.clock import Clock

logger = logging.getLogger(__name__)


class AdminScreen(Screen):
    def export_csv(self):
        try:
            export_dir = get_export_directory()
            filename = os.path.join(
                export_dir,
                f"timeclock_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            entries = get_time_entries_for_export()
            entry_count = entries.count()
            
            if entry_count == 0:
                App.get_running_app().show_popup("Export Info", "No time entries to export.")
                return
            fieldnames = ['Employee Name', 'Tag ID', 'Action', 'Timestamp']
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in entries:
                try:
                    writer.writerow({
                        'Employee Name': entry.employee.name,
                        'Tag ID': entry.employee.rfid_tag,
                        'Action': entry.action.upper(),
                        'Timestamp': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    logger.warning(f"Skipping entry due to error: {e}")
                    continue

            write_file(buffer.getvalue().encode('utf-8'), filename)
            
            App.get_running_app().show_popup(
                "Export Success", 
                f"Export ({entry_count} entries) saved to:\n{filename}"
            )
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            App.get_running_app().show_popup("Export Error", f"Failed to export: {str(e)}")

    def export_database(self):
        temp_path = None
        try:
            export_dir = get_export_directory()
            filename = os.path.join(
                export_dir,
                f"timeclock_db_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite"
            )

            db_path = os.path.abspath(db.database)
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                temp_path = tmp.name

            source_conn = sqlite3.connect(db_path, timeout=10)
            dest_conn = sqlite3.connect(temp_path)
            source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()

            with open(temp_path, "rb") as f:
                db_bytes = f.read()

            write_file(db_bytes, filename)
            App.get_running_app().show_popup(
                "Export Success",
                f"Database export saved to:\n{filename}"
            )
        except Exception as e:
            logger.error(f"Database export failed: {e}")
            App.get_running_app().show_popup("Export Error", f"Failed to export database: {str(e)}")
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not remove temp file {temp_path}: {cleanup_error}")
    
    def export_all_employees_lgav(self):
        """Export LGAV Excel report for all employees (one sheet per employee) for the last year"""
        try:
            export_dir = get_export_directory()
            filename = generate_all_employees_lgav_excel(export_root=export_dir)
            
            App.get_running_app().show_popup(
                "Export Erfolgreich",
                f"LGAV Report für alle Mitarbeiter exportiert nach:\n{filename}"
            )
        except Exception as e:
            logger.error(f"LGAV export for all employees failed: {e}")
            App.get_running_app().show_popup("Export Error", f"Export fehlgeschlagen: {str(e)}")

