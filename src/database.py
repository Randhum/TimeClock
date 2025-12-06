from peewee import *
import datetime
import logging

logger = logging.getLogger(__name__)

db = SqliteDatabase('timeclock.db')

class BaseModel(Model):
    class Meta:
        database = db

class Employee(BaseModel):
    name = CharField(max_length=100, null=False)
    rfid_tag = CharField(max_length=50, unique=True, null=False, index=True)
    is_admin = BooleanField(default=False, null=False)
    created_at = DateTimeField(default=datetime.datetime.now, null=False)
    active = BooleanField(default=True, null=False)  # Soft delete support
    
    class Meta:
        indexes = (
            (('rfid_tag',), True),  # Unique index
        )
    
    def __str__(self):
        return f"{self.name} ({self.rfid_tag})"

class TimeEntry(BaseModel):
    employee = ForeignKeyField(Employee, backref='time_entries', on_delete='CASCADE', null=False)
    timestamp = DateTimeField(default=datetime.datetime.now, null=False, index=True)
    action = CharField(max_length=10, null=False)  # 'in' or 'out'
    active = BooleanField(default=True, null=False)
    
    class Meta:
        indexes = (
            (('employee', 'timestamp'), False),  # Composite index for queries
            (('timestamp',), False),  # Index for sorting
        )
    
    def __str__(self):
        return f"{self.employee.name} - {self.action.upper()} @ {self.timestamp}"
    
    @staticmethod
    def get_last_for_employee(employee):
        """Get last entry for an employee"""
        return TimeEntry.select().where(
            TimeEntry.employee == employee,
            TimeEntry.active == True
        ).order_by(TimeEntry.timestamp.desc()).first()

def ensure_db_connection():
    """Ensure database connection is open"""
    if db.is_closed():
        try:
            db.connect(reuse_if_open=True)
            logger.debug("Database connection opened")
        except Exception as e:
            logger.error(f"Failed to open database connection: {e}")
            raise


def _ensure_timeentry_active_column():
    """Add `active` column to TimeEntry if missing"""
    ensure_db_connection()
    try:
        rows = db.execute_sql("PRAGMA table_info(timeentry)").fetchall()
        columns = [row[1] for row in rows]
        if 'active' not in columns:
            db.execute_sql("ALTER TABLE timeentry ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1")
            logger.info("Added 'active' column to TimeEntry table")
    except Exception as exc:
        logger.debug(f"Could not ensure active column: {exc}")


def soft_delete_time_entries(entry_ids):
    """Soft-delete specific time entries (set active=False)"""
    if not entry_ids:
        return 0
    ensure_db_connection()
    return TimeEntry.update(active=False).where(TimeEntry.id.in_(entry_ids)).execute()

def initialize_db():
    """Initialize database connection and create tables"""
    try:
        # Ensure connection is open
        ensure_db_connection()
        db.create_tables([Employee, TimeEntry], safe=True)
        _ensure_timeentry_active_column()
        # Ensure changes are committed
        db.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        try:
            db.rollback()
        except:
            pass
        raise

def close_db():
    """Close database connection, ensuring all data is committed"""
    try:
        if not db.is_closed():
            # Ensure all pending transactions are committed
            db.commit()
            db.close()
            logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
        # Try to close anyway
        try:
            if not db.is_closed():
                db.close()
        except:
            pass

def get_employee_by_tag(tag_id):
    """Safely get employee by RFID tag"""
    ensure_db_connection()
    try:
        return Employee.get(Employee.rfid_tag == tag_id, Employee.active == True)
    except Employee.DoesNotExist:
        return None

def get_all_employees(include_inactive=False):
    """Get all employees, optionally including inactive ones"""
    ensure_db_connection()
    query = Employee.select()
    if not include_inactive:
        query = query.where(Employee.active == True)
    return query.order_by(Employee.name)

def get_admin_count():
    """Get count of active admin employees"""
    ensure_db_connection()
    return Employee.select().where(
        Employee.is_admin == True,
        Employee.active == True
    ).count()

def create_employee(name, rfid_tag, is_admin=False):
    """Create a new employee with validation and ensure data is committed"""
    if not name or len(name.strip()) == 0:
        raise ValueError("Employee name cannot be empty")
    if not rfid_tag or len(rfid_tag.strip()) < 4:
        raise ValueError("RFID tag must be at least 4 characters")
    
    ensure_db_connection()
    
    try:
        # Use atomic transaction to ensure data integrity
        # db.atomic() automatically commits on successful exit
        with db.atomic():
            employee = Employee.create(
                name=name.strip(),
                rfid_tag=rfid_tag.strip().upper(),
                is_admin=bool(is_admin)
            )
            logger.info(f"Employee created successfully: {employee.name} ({employee.rfid_tag})")
            return employee
    except IntegrityError as e:
        logger.error(f"Failed to create employee (integrity error): {e}")
        # db.atomic() automatically rolls back on exception
        raise
    except Exception as e:
        logger.error(f"Failed to create employee: {e}")
        # db.atomic() automatically rolls back on exception
        raise

def create_time_entry(employee, action):
    """Create a time entry with validation and ensure data is committed"""
    if action not in ('in', 'out'):
        raise ValueError(f"Invalid action: {action}. Must be 'in' or 'out'")
    
    if not employee.active:
        raise ValueError("Cannot create time entry for inactive employee")
    
    # Ensure database connection is open
    ensure_db_connection()
    
    try:
        # Use atomic transaction to ensure data integrity
        # db.atomic() automatically commits on successful exit
        with db.atomic():
            timestamp = datetime.datetime.now()
            entry = TimeEntry.create(
                employee=employee,
                action=action,
                timestamp=timestamp
            )
            logger.info(f"Time entry created: {employee.name} - {action.upper()} @ {timestamp}")
            return entry
    except Exception as e:
        logger.error(f"Failed to create time entry: {e}")
        # db.atomic() automatically rolls back on exception
        raise

def get_time_entries_for_export():
    """Get all time entries formatted for CSV export"""
    ensure_db_connection()
    return TimeEntry.select().join(Employee).where(
        Employee.active == True,
        TimeEntry.active == True
    ).order_by(TimeEntry.timestamp.desc())
