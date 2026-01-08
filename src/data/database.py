"""
Database module for TimeClock application.
Uses SQLCipher for transparent AES-256 encryption at rest.
"""
import datetime
import logging
import os
import sys
import time
import threading

from peewee import (
    Model, CharField, BooleanField, DateTimeField, DateField, IntegerField, TextField,
    ForeignKeyField, IntegrityError, OperationalError
)

logger = logging.getLogger(__name__)

# Environment variable for the encryption key
ENV_KEY_NAME = "TIMECLOCK_ENV_KEY"
DB_FILE = "timeclock.db"


def _get_database():
    """
    Create and return the appropriate database connection.
    Uses SQLCipher if TIMECLOCK_ENV_KEY is set, otherwise falls back to plain SQLite.
    """
    passphrase = os.getenv(ENV_KEY_NAME)
    
    if passphrase:
        # Use SQLCipher for encrypted database
        try:
            from playhouse.sqlcipher_ext import SqlCipherDatabase
            logger.info("SQLCipher encryption enabled")
            return SqlCipherDatabase(
                DB_FILE,
                passphrase=passphrase,
                # SQLCipher 4.x settings for maximum security
                pragmas={
                    'kdf_iter': 256000,  # Key derivation iterations
                    'cipher_page_size': 4096,
                    'cipher_use_hmac': True,
                }
            )
        except ImportError:
            logger.error(
                "SQLCipher not available! Install with: pip install sqlcipher3-binary\n"
                "Database will NOT be encrypted."
            )
            # Fall through to plain SQLite
    else:
        logger.warning(
            f"No encryption key set. Set {ENV_KEY_NAME} environment variable "
            "for encrypted database. Running with UNENCRYPTED database!"
        )
    
    # Fallback to plain SQLite (development/unset key)
    from peewee import SqliteDatabase
    return SqliteDatabase(DB_FILE)


# Initialize database connection
db = _get_database()

# Employee-level locks to prevent concurrent modifications
_employee_locks = {}
_locks_lock = threading.Lock()


def _get_employee_lock(employee_id):
    """Get or create a lock for a specific employee"""
    with _locks_lock:
        if employee_id not in _employee_locks:
            _employee_locks[employee_id] = threading.Lock()
        return _employee_locks[employee_id]


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

    @staticmethod
    def get_last_before_timestamp(employee, timestamp):
        """
        Get the last entry for an employee before a given timestamp.
        
        Args:
            employee: Employee object
            timestamp: datetime to find entries before
            
        Returns:
            TimeEntry or None if no entry found
        """
        return TimeEntry.select().where(
            TimeEntry.employee == employee,
            TimeEntry.active == True,
            TimeEntry.timestamp < timestamp
        ).order_by(TimeEntry.timestamp.desc()).first()


class LgavDayEntry(BaseModel):
    """L-GAV day type entry for tracking holidays, vacation, sick days, etc."""
    employee = ForeignKeyField(Employee, backref='lgav_entries', on_delete='CASCADE', null=False)
    date = DateField(null=False)
    upper_code = CharField(max_length=10, null=True)  # A, X, FT, F, K, U, Mu, Mi, D
    lower_code = CharField(max_length=10, null=True)  # HH:MM format or code
    total_seconds = IntegerField(default=0)
    notes = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now, null=False)
    updated_at = DateTimeField(default=datetime.datetime.now, null=False)
    active = BooleanField(default=True, null=False)

    class Meta:
        indexes = (
            (('employee', 'date'), True),  # Unique composite index
            (('date',), False),  # Index for date range queries
        )

    def __str__(self):
        return f"{self.employee.name} - {self.date} [{self.upper_code}/{self.lower_code}]"


def is_encrypted() -> bool:
    """Check if the database is using SQLCipher encryption."""
    try:
        from playhouse.sqlcipher_ext import SqlCipherDatabase
        return isinstance(db, SqlCipherDatabase)
    except ImportError:
        return False


def ensure_db_connection(max_retries=3, initial_delay=0.1):
    """
    Ensure database connection is open with retry logic for transient errors.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 0.1)
        
    Raises:
        Exception: If connection fails after all retries
    """
    if not db.is_closed():
        return  # Already connected
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            db.connect(reuse_if_open=True)
            logger.debug("Database connection opened")
            return
        except (OperationalError, Exception) as e:
            last_exception = e
            error_msg = str(e).lower()
            
            # Check if this is a transient error that we should retry
            is_transient = any(keyword in error_msg for keyword in [
                'locked', 'busy', 'database is locked', 'unable to open database',
                'timeout', 'connection', 'temporary'
            ])
            
            if is_transient and attempt < max_retries - 1:
                # Exponential backoff: delay increases with each retry
                delay = initial_delay * (2 ** attempt)
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                # Not a transient error or out of retries
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying...")
                    time.sleep(initial_delay * (2 ** attempt))
                else:
                    logger.error(f"Failed to open database connection after {max_retries} attempts: {e}")
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


def _ensure_lgav_day_entry_table():
    """Ensure LgavDayEntry table exists"""
    ensure_db_connection()
    try:
        db.create_tables([LgavDayEntry], safe=True)
        logger.info("LgavDayEntry table ensured")
    except Exception as exc:
        logger.debug(f"Could not ensure LgavDayEntry table: {exc}")


def soft_delete_time_entries(entry_ids):
    """Soft-delete specific time entries (set active=False) with transaction and error handling"""
    if not entry_ids:
        return 0
    ensure_db_connection()
    try:
        with db.atomic():
            result = TimeEntry.update(active=False).where(TimeEntry.id.in_(entry_ids)).execute()
            db.commit()  # Explicit commit
            return result
    except Exception as e:
        logger.error(f"Failed to soft-delete time entries: {e}")
        try:
            db.rollback()
        except:
            pass
        raise


def initialize_db():
    """Initialize database connection and create tables"""
    try:
        ensure_db_connection()
        
        # Log encryption status
        if is_encrypted():
            logger.info("Database is ENCRYPTED with SQLCipher")
        else:
            logger.warning("Database is NOT encrypted!")
        
        db.create_tables([Employee, TimeEntry], safe=True)
        _ensure_timeentry_active_column()
        _ensure_lgav_day_entry_table()
        db.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        raise


def close_db():
    """Close database connection, ensuring all data is committed"""
    try:
        if not db.is_closed():
            db.commit()
            db.close()
            logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
        try:
            if not db.is_closed():
                db.close()
        except Exception:
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
        with db.atomic():
            employee = Employee.create(
                name=name.strip(),
                rfid_tag=rfid_tag.strip().upper(),
                is_admin=bool(is_admin)
            )
            db.commit()  # Explicit commit to ensure data is persisted
            logger.info(f"Employee created successfully: {employee.name} ({employee.rfid_tag})")
            return employee
    except IntegrityError as e:
        logger.error(f"Failed to create employee (integrity error): {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Failed to create employee: {e}")
        try:
            db.rollback()
        except:
            pass
        raise


def create_time_entry(employee, action, timestamp=None):
    """
    Create a time entry with validation and ensure data is committed.
    
    Args:
        employee: Employee object
        action: 'in' or 'out'
        timestamp: Optional datetime (defaults to now)
        
    Returns:
        Created TimeEntry object
    """
    if action not in ('in', 'out'):
        raise ValueError(f"Invalid action: {action}. Must be 'in' or 'out'")

    if not employee.active:
        raise ValueError("Cannot create time entry for inactive employee")
    
    if timestamp is None:
        timestamp = datetime.datetime.now()
    else:
        # Validate timestamp is reasonable
        now = datetime.datetime.now()
        max_future = now + datetime.timedelta(days=1)  # Allow 1 day in future
        min_past = now - datetime.timedelta(days=365)  # Allow 1 year in past
        
        if timestamp > max_future:
            raise ValueError(f"Timestamp cannot be more than 1 day in the future. Got: {timestamp}")
        if timestamp < min_past:
            raise ValueError(f"Timestamp cannot be more than 1 year in the past. Got: {timestamp}")

    ensure_db_connection()

    try:
        with db.atomic():
            entry = TimeEntry.create(
                employee=employee,
                action=action,
                timestamp=timestamp
            )
            db.commit()  # Explicit commit to ensure data is persisted
            logger.info(f"Time entry created: {employee.name} - {action.upper()} @ {timestamp}")
            return entry
    except Exception as e:
        logger.error(f"Failed to create time entry: {e}")
        try:
            db.rollback()
        except:
            pass
        raise


def create_time_entry_atomic(employee):
    """
    Atomically determine action and create time entry to prevent race conditions.
    This ensures that action determination and entry creation happen in a single transaction.
    Uses employee-level locking to prevent concurrent modifications.
    
    Args:
        employee: Employee to clock in/out
        
    Returns:
        Tuple of (entry, action) where entry is the created TimeEntry and action is 'in' or 'out'
        
    Raises:
        ValueError: If employee is inactive or invalid
        DatabaseError: If database operation fails
    """
    if not employee.active:
        raise ValueError("Cannot create time entry for inactive employee")
    
    # Acquire employee-specific lock to prevent concurrent modifications
    employee_lock = _get_employee_lock(employee.id)
    
    with employee_lock:
        ensure_db_connection()
        
        try:
            with db.atomic():
                # Get last entry within transaction to prevent race conditions
                last_entry = TimeEntry.get_last_for_employee(employee)
                
                # Determine action based on last entry
                if not last_entry or last_entry.action == 'out':
                    action = 'in'
                else:
                    action = 'out'
                
                # Create entry immediately within same transaction
                timestamp = datetime.datetime.now()
                # Timestamp validation is implicit (current time is always valid)
                entry = TimeEntry.create(
                    employee=employee,
                    action=action,
                    timestamp=timestamp
                )
                db.commit()  # Explicit commit to ensure data is persisted
                logger.info(f"Time entry created atomically: {employee.name} - {action.upper()} @ {timestamp}")
                return entry, action
        except Exception as e:
            logger.error(f"Failed to create time entry atomically: {e}")
            try:
                db.rollback()
            except:
                pass
        raise


def get_time_entries_for_export():
    """Get all time entries formatted for CSV export"""
    ensure_db_connection()
    return TimeEntry.select().join(Employee).where(
        Employee.active == True,
        TimeEntry.active == True
    ).order_by(TimeEntry.timestamp.desc())


# --- L-GAV Day Entry Functions ---

def create_lgav_day_entry(employee, date, upper_code=None, lower_code=None, 
                          total_seconds=0, notes=None):
    """
    Create or update an L-GAV day entry.
    
    Args:
        employee: Employee object
        date: datetime.date object
        upper_code: L-GAV upper field code (A, X, FT, F, K, U, Mu, Mi, D)
        lower_code: L-GAV lower field (HH:MM format or code)
        total_seconds: Total seconds worked (for work days)
        notes: Optional notes
    
    Returns:
        LgavDayEntry object
    """
    ensure_db_connection()
    
    if not employee.active:
        raise ValueError("Cannot create L-GAV entry for inactive employee")
    
    try:
        with db.atomic():
            # Try to get existing entry
            try:
                entry = LgavDayEntry.get(
                    LgavDayEntry.employee == employee,
                    LgavDayEntry.date == date,
                    LgavDayEntry.active == True
                )
                # Update existing entry
                entry.upper_code = upper_code
                entry.lower_code = lower_code
                entry.total_seconds = total_seconds
                entry.notes = notes
                entry.updated_at = datetime.datetime.now()
                entry.save()
                db.commit()  # Explicit commit
                logger.info(f"Updated L-GAV entry for {employee.name} on {date}")
                return entry
            except LgavDayEntry.DoesNotExist:
                # Create new entry
                entry = LgavDayEntry.create(
                    employee=employee,
                    date=date,
                    upper_code=upper_code,
                    lower_code=lower_code,
                    total_seconds=total_seconds,
                    notes=notes
                )
                db.commit()  # Explicit commit
                logger.info(f"Created L-GAV entry for {employee.name} on {date}")
                return entry
    except IntegrityError as e:
        logger.error(f"Failed to create L-GAV entry (integrity error): {e}")
        try:
            db.rollback()
        except:
            pass
        raise
    except Exception as e:
        logger.error(f"Failed to create L-GAV entry: {e}")
        try:
            db.rollback()
        except:
            pass
        raise


def get_lgav_day_entry(employee, date):
    """
    Get L-GAV entry for a specific employee and date.
    
    Args:
        employee: Employee object
        date: datetime.date object
    
    Returns:
        LgavDayEntry object or None if not found
    """
    ensure_db_connection()
    try:
        return LgavDayEntry.get(
            LgavDayEntry.employee == employee,
            LgavDayEntry.date == date,
            LgavDayEntry.active == True
        )
    except LgavDayEntry.DoesNotExist:
        return None


def get_lgav_day_entries(employee, start_date, end_date):
    """
    Get all L-GAV entries for an employee in a date range.
    
    Args:
        employee: Employee object
        start_date: datetime.date object
        end_date: datetime.date object
    
    Returns:
        List of LgavDayEntry objects
    """
    ensure_db_connection()
    return list(LgavDayEntry.select().where(
        LgavDayEntry.employee == employee,
        LgavDayEntry.date >= start_date,
        LgavDayEntry.date <= end_date,
        LgavDayEntry.active == True
    ).order_by(LgavDayEntry.date.asc()))


def update_lgav_day_entry(entry_id, **kwargs):
    """
    Update an existing L-GAV day entry.
    
    Args:
        entry_id: ID of the entry to update
        **kwargs: Fields to update (upper_code, lower_code, total_seconds, notes)
    
    Returns:
        Updated LgavDayEntry object
    """
    ensure_db_connection()
    try:
        entry = LgavDayEntry.get(LgavDayEntry.id == entry_id, LgavDayEntry.active == True)
        
        # Update allowed fields
        allowed_fields = ['upper_code', 'lower_code', 'total_seconds', 'notes']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(entry, field, value)
        
        entry.updated_at = datetime.datetime.now()
        entry.save()
        logger.info(f"Updated L-GAV entry {entry_id}")
        return entry
    except LgavDayEntry.DoesNotExist:
        raise ValueError(f"L-GAV entry {entry_id} not found")
    except Exception as e:
        logger.error(f"Failed to update L-GAV entry: {e}")
        raise


def delete_lgav_day_entry(entry_id):
    """
    Soft delete an L-GAV day entry.
    
    Args:
        entry_id: ID of the entry to delete
    
    Returns:
        Number of rows affected
    """
    ensure_db_connection()
    try:
        return LgavDayEntry.update(active=False).where(
            LgavDayEntry.id == entry_id
        ).execute()
    except Exception as e:
        logger.error(f"Failed to delete L-GAV entry: {e}")
        raise


# --- Migration Utility ---

def migrate_to_encrypted(passphrase: str, source_db: str = "timeclock.db", 
                         target_db: str = "timeclock_encrypted.db") -> bool:
    """
    Migrate an unencrypted database to an encrypted one.
    
    Args:
        passphrase: The encryption passphrase to use
        source_db: Path to the unencrypted source database
        target_db: Path for the new encrypted database
    
    Returns:
        True if migration succeeded, False otherwise
    """
    try:
        from playhouse.sqlcipher_ext import SqlCipherDatabase
    except ImportError:
        logger.error("SQLCipher not available. Install with: pip install sqlcipher3-binary")
        return False
    
    import sqlite3
    
    if not os.path.exists(source_db):
        logger.error(f"Source database not found: {source_db}")
        return False
    
    if os.path.exists(target_db):
        logger.error(f"Target database already exists: {target_db}")
        return False
    
    try:
        # Open source (unencrypted)
        source_conn = sqlite3.connect(source_db)
        
        # Create encrypted target
        encrypted_db = SqlCipherDatabase(
            target_db,
            passphrase=passphrase,
            pragmas={
                'kdf_iter': 256000,
                'cipher_page_size': 4096,
                'cipher_use_hmac': True,
            }
        )
        encrypted_db.connect()
        
        # Get the raw connection for ATTACH
        target_conn = encrypted_db.connection()
        
        # Backup source to target
        source_conn.backup(target_conn)
        
        source_conn.close()
        encrypted_db.close()
        
        logger.info(f"Successfully migrated {source_db} -> {target_db} (encrypted)")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
