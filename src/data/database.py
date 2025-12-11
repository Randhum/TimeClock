"""
Database module for TimeClock application.
Uses SQLCipher for transparent AES-256 encryption at rest.
"""
import datetime
import logging
import os
import sys

from peewee import (
    Model, CharField, BooleanField, DateTimeField, ForeignKeyField, IntegrityError
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


def is_encrypted() -> bool:
    """Check if the database is using SQLCipher encryption."""
    try:
        from playhouse.sqlcipher_ext import SqlCipherDatabase
        return isinstance(db, SqlCipherDatabase)
    except ImportError:
        return False


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
        ensure_db_connection()
        
        # Log encryption status
        if is_encrypted():
            logger.info("Database is ENCRYPTED with SQLCipher")
        else:
            logger.warning("Database is NOT encrypted!")
        
        db.create_tables([Employee, TimeEntry], safe=True)
        _ensure_timeentry_active_column()
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
            logger.info(f"Employee created successfully: {employee.name} ({employee.rfid_tag})")
            return employee
    except IntegrityError as e:
        logger.error(f"Failed to create employee (integrity error): {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create employee: {e}")
        raise


def create_time_entry(employee, action):
    """Create a time entry with validation and ensure data is committed"""
    if action not in ('in', 'out'):
        raise ValueError(f"Invalid action: {action}. Must be 'in' or 'out'")

    if not employee.active:
        raise ValueError("Cannot create time entry for inactive employee")

    ensure_db_connection()

    try:
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
        raise


def get_time_entries_for_export():
    """Get all time entries formatted for CSV export"""
    ensure_db_connection()
    return TimeEntry.select().join(Employee).where(
        Employee.active == True,
        TimeEntry.active == True
    ).order_by(TimeEntry.timestamp.desc())


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
