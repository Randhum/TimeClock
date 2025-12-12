# TimeClock Architecture Documentation

> Technical documentation for developers and system integrators

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Directory Structure](#directory-structure)
4. [Core Components](#core-components)
5. [Data Flow](#data-flow)
6. [Database Schema](#database-schema)
7. [Service Layer](#service-layer)
8. [RFID Subsystem](#rfid-subsystem)
9. [Report Engine](#report-engine)
10. [Development Guide](#development-guide)

---

## System Overview

TimeClock follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  Screens • Popups • Widgets • UI Logic                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                    BUSINESS LAYER                           │
│  ClockService • StateService • PopupService                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                    DATA LAYER
│  Database Models • Queries • Transactions                   │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                    HARDWARE LAYER                           │
│  RFID Provider • USB Detection                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Layers

### Presentation Layer (`src/presentation/`)

**Screens** (`screens/`):
- `TimeClockScreen` - Main clock interface
- `AdminScreen` - Admin panel
- `RegisterScreen` - Employee registration
- `IdentifyScreen` - Badge identification
- `WTReportSelectEmployeeScreen` - Report employee selection
- `WTReportSelectDatesScreen` - Report date selection
- `WTReportDisplayScreen` - Report display

**Popups** (`popups/`):
- `GreeterPopup` - Welcome/goodbye messages
- `BadgeIdentificationPopup` - Badge scan prompt
- `EntryEditorPopup` - Edit time entries
- `DatePickerPopup` / `LimitedDatePickerPopup` - Date selection
- `TimePickerPopup` - Time selection
- `AddEntryPopup` - Manual entry form

**Widgets** (`widgets/`):
- `DebouncedButton` - Prevents double-clicks
- `FilteredTextInput` - Filters duplicate keystrokes
- `GlobalInputFilter` - App-wide touch deduplication
- `GlobalKeyFilter` - App-wide keyboard deduplication

### Business Layer (`src/services/`)

**ClockService** (`clock_service.py`):
- Handles clock in/out logic
- Determines next action (IN/OUT)
- Manages RFID LED feedback
- Returns `ClockResult` dataclass

**StateService** (`state_service.py`):
- Manages `last_clocked_employee` with timeout
- Handles scan debouncing (`is_recent_scan`)
- Manages `pending_identification` state

**PopupService** (`popup_service.py`):
- Centralized popup management
- `show_info()`, `show_error()`, `show_success()`, `show_greeter()`

### Data Layer (`src/data/database.py`)

- **Models**: `Employee`, `TimeEntry`
- **Queries**: Tag lookup, entry retrieval, export queries
- **Transactions**: Atomic operations with explicit commits
- **Soft Delete**: Entries marked `active=False` for audit trail

**Static Data** (`src/data/greetings/`):
- Greeting message files for different languages and shifts

### Hardware Layer (`src/hardware/`)

**RFID Abstraction** (`rfid.py`):
- **RFIDProvider**: Abstract base class
- **PcProxRFIDProvider**: Real hardware implementation
- **MockRFIDProvider**: Development/testing fallback
- Background thread polling with main-thread callbacks

**Hardware Drivers**:
- `pcprox.py` - pcProx RFID reader driver
- `configure.py` - Hardware configuration utilities
- `usbtest.py` - USB device testing utilities
- `protocol.md` - Hardware protocol documentation

---

## Directory Structure

```
src/
├── main.py                    # Application entry point
│
├── services/                 # Business logic layer
│   ├── clock_service.py      # Clock in/out logic
│   ├── state_service.py      # State management
│   ├── popup_service.py      # Popup management
│   └── report_service.py     # Report generation engine
│
├── presentation/             # UI layer
│   ├── timeclock.kv          # UI layout definitions
│   ├── screens/              # Screen controllers
│   │   ├── timeclock_screen.py
│   │   ├── admin_screen.py
│   │   ├── register_screen.py
│   │   ├── identify_screen.py
│   │   ├── screensaver_screen.py
│   │   └── wtreport_*.py
│   ├── popups/               # Popup components
│   │   ├── greeter_popup.py
│   │   ├── badge_identification_popup.py
│   │   ├── entry_editor_popup.py
│   │   ├── add_entry_popup.py
│   │   └── *_picker_popup.py
│   └── widgets/              # Custom widgets
│       ├── debounced_button.py
│       ├── filtered_text_input.py
│       └── input_filters.py
│
├── hardware/                 # Hardware layer
│   ├── pcprox.py             # RFID reader driver
│   ├── configure.py          # Hardware configuration
│   └── usbtest.py            # USB testing utilities
│
├── utils/                    # Utilities
│   ├── errors.py             # Error classes
│   └── export_utils.py       # Export utilities
│
└── data/                     # Data files
    └── greetings/            # Greeting message files
```

---

## Core Components

### Application Entry Point (`main.py`)

**TimeClockApp**:
- Initializes services
- Manages screen navigation
- Handles RFID scan events
- Manages idle timer and screensaver
- Coordinates between services and UI

**Key Methods**:
- `build()` - Initializes database, RFID, services
- `handle_scan()` - Routes RFID scans to appropriate handlers
- `perform_clock_action()` - Delegates to ClockService
- `on_rfid_scan()` - RFID callback (scheduled to main thread)

### Database Layer (`database.py`)

**Models**:
```python
class Employee(Model):
    name = CharField(max_length=100)
    rfid_tag = CharField(max_length=50, unique=True, index=True)
    is_admin = BooleanField(default=False)
    active = BooleanField(default=True)

class TimeEntry(Model):
    employee = ForeignKeyField(Employee)
    timestamp = DateTimeField(index=True)
    action = CharField(max_length=10)  # 'in' or 'out'
    active = BooleanField(default=True)
```

**Key Functions**:
- `initialize_db()` - Creates tables, ensures connection
- `get_employee_by_tag()` - Lookup by RFID tag
- `create_time_entry()` - Atomic entry creation
- `soft_delete_time_entries()` - Mark entries inactive

### Report Engine (`wt_report.py`)

**WorkingTimeReport**:
- FIFO pairing algorithm for clock events
- Daily aggregation and totals
- Text and CSV output formats

**Session Pairing**:
- Uses queue-based FIFO algorithm
- Pairs clock-in with next clock-out
- Handles duplicate scans gracefully
- Flags open sessions (missing clock-out)

---

## Data Flow

### Clock Action Flow

```
RFID Scan
    │
    ▼
handle_scan() [main.py]
    │
    ├─ StateService.is_recent_scan() → Debounce check
    │
    ├─ get_employee_by_tag() → Database lookup
    │
    └─ perform_clock_action()
           │
           └─ ClockService.clock_in_out()
                  │
                  ├─ Get last entry
                  ├─ Determine action (IN/OUT)
                  ├─ Create time entry
                  └─ Return ClockResult
           │
           ├─ PopupService.show_greeter()
           ├─ StateService.set_last_clocked_employee()
           └─ Update UI status
```

### Report Generation Flow

```
Admin selects employee + dates
    │
    ▼
WTReportSelectDatesScreen
    │
    └─ Generate Report button
           │
           └─ generate_wt_report(employee, start, end)
                  │
                  ├─ Query time entries
                  ├─ Group by day
                  ├─ FIFO pairing per day
                  ├─ Calculate durations
                  └─ Aggregate totals
           │
           └─ Display in WTReportDisplayScreen
```

---

## Database Schema

### Employee Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `name` | VARCHAR(100) | NOT NULL | Employee full name |
| `rfid_tag` | VARCHAR(50) | UNIQUE, NOT NULL, INDEXED | RFID badge identifier |
| `is_admin` | BOOLEAN | DEFAULT FALSE | Administrator flag |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Registration timestamp |
| `active` | BOOLEAN | DEFAULT TRUE | Soft delete flag |

### TimeEntry Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `employee_id` | INTEGER | FOREIGN KEY → Employee | Employee reference |
| `timestamp` | DATETIME | NOT NULL, INDEXED | Clock action time |
| `action` | VARCHAR(10) | NOT NULL | 'in' or 'out' |
| `active` | BOOLEAN | DEFAULT TRUE | Soft delete flag |

**Indexes**:
- `rfid_tag` on Employee (for fast lookups)
- `timestamp` on TimeEntry (for report queries)

---

## Service Layer

### ClockService

**Purpose**: Encapsulates clock in/out business logic

**Key Methods**:
```python
def clock_in_out(employee: Employee) -> ClockResult:
    """Perform clock action, returns result with success/error"""
    
def _determine_action(last_entry: Optional[TimeEntry]) -> str:
    """Determine next action: 'in' or 'out'"""
```

**Dependencies**:
- RFID provider (for LED feedback)
- PopupService (for error messages)
- StateService (for state updates)

### StateService

**Purpose**: Centralized application state management

**Key Methods**:
```python
def is_recent_scan(tag_id: str, threshold: float = 1.2) -> bool:
    """Check if scan is within debounce threshold"""
    
def set_last_clocked_employee(employee: Employee, timeout: int = 120):
    """Set last clocked employee with timeout"""
    
def set_pending_identification(action_type: str, popup: Popup):
    """Store pending badge identification request"""
```

**State Managed**:
- Last clocked employee (with timeout)
- Recent scan times (for debouncing)
- Pending identification requests

### PopupService

**Purpose**: Consistent popup display across application

**Key Methods**:
```python
def show_info(title: str, message: str, duration: float = 3.0):
    """Show informational popup"""
    
def show_error(title: str, message: str, duration: float = 5.0):
    """Show error popup"""
    
def show_greeter(employee: Employee, action: str):
    """Show greeting popup with random message"""
```

---

## RFID Subsystem

### Provider Architecture

```python
class RFIDProvider(ABC):
    """Abstract base class for RFID readers"""
    
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._running = False
        self._thread = None
        self._command_queue = Queue()
    
    def start(self):
        """Start background polling thread"""
        
    def stop(self):
        """Signal thread termination"""
        
    def indicate_success(self):
        """Queue green LED command"""
        
    def indicate_error(self):
        """Queue red LED command"""
```

### Threading Model

| Thread | Purpose | Communication |
|--------|---------|---------------|
| **Main Thread** | Kivy event loop, UI rendering | Direct method calls |
| **RFID Thread** | HID polling, tag detection | `Clock.schedule_once()` → Main |

**Thread Safety**: All RFID callbacks are scheduled on the main thread via Kivy's `Clock`, ensuring UI and database operations are single-threaded.

### Scan Debouncing

Prevents duplicate clock entries from rapid scans:

```python
# In StateService
def is_recent_scan(self, tag_id: str, threshold: float = 1.2) -> bool:
    """Check if scan is within debounce threshold"""
    now = time.time()
    last_scan = self._recent_scans.get(tag_id, 0)
    
    if now - last_scan < threshold:
        return True
    
    self._recent_scans[tag_id] = now
    return False
```

---

## Report Engine

### FIFO Pairing Algorithm

The report engine uses a **queue-based FIFO** algorithm to pair clock-in and clock-out events:

```python
def _process_day_entries(entries: List[TimeEntry]) -> List[Session]:
    sessions = []
    pending_ins = deque()  # Queue of unmatched clock-ins
    
    for entry in entries:  # Chronologically sorted
        if entry.action == 'in':
            pending_ins.append((entry.timestamp, entry.id))
        
        elif entry.action == 'out':
            if not pending_ins:
                logger.warning("Clock-out without clock-in")
                continue
            
            clock_in_time, clock_in_id = pending_ins.popleft()
            duration = entry.timestamp - clock_in_time
            
            sessions.append({
                'clock_in': clock_in_time,
                'clock_out': entry.timestamp,
                'duration': duration,
                'clock_in_entry_id': clock_in_id,
                'clock_out_entry_id': entry.id
            })
    
    # Any remaining pending_ins are open sessions
    return sessions
```

**Example**:
```
Entries: 08:00 IN, 08:01 IN, 12:00 OUT, 12:01 OUT, 13:00 IN, 17:00 OUT

Sessions:
  Session 1: 08:00 → 12:00 (4h 00m)  [IDs: 1, 3]
  Session 2: 08:01 → 12:01 (4h 00m)  [IDs: 2, 4] ← Duplicate
  Session 3: 13:00 → 17:00 (4h 00m)  [IDs: 5, 6]
```

---

## Development Guide

### Running in Development Mode

**With Mock RFID**:
```python
# In src/main.py
self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=True)
```

**Logging**:
```python
# Debug logging enabled by default
logging.basicConfig(level=logging.DEBUG)
```

### Adding a New Screen

1. Create screen class in `src/presentation/screens/`
2. Add to `screens/__init__.py`
3. Define UI in `timeclock.kv`
4. Add navigation logic in `main.py`

### Adding a New Service

1. Create service class in `src/services/`
2. Add to `services/__init__.py`
3. Initialize in `TimeClockApp.__init__()`
4. Inject dependencies as needed

### Testing

**Unit Tests** (Future):
- Test services independently
- Mock dependencies
- Test business logic without UI

**Integration Tests** (Future):
- Test complete workflows
- Test database operations
- Test RFID integration

### Code Style

- Follow PEP 8
- Use type hints where possible
- Document public APIs
- Keep functions focused and small

---

## Performance Considerations

### Database

- **Indexes**: `rfid_tag` and `timestamp` are indexed for fast queries
- **Connection Reuse**: Single connection, ensured before each operation
- **Transactions**: Atomic operations with explicit commits

### UI

- **Debouncing**: RFID scans debounced at 1.2s
- **Lazy Loading**: Employee lists populated on screen enter
- **Scheduled Updates**: UI updates via `Clock.schedule_once()`

### Memory

- **Report Generation**: Processes entries in batches by day
- **Export**: Streams to file, doesn't hold full dataset in memory

---

## Security Model

### Access Control

| Resource | Employee | Admin |
|----------|----------|-------|
| Clock In/Out | ✓ | ✓ |
| View Own Summary | ✓ | ✓ |
| Edit Own Sessions | ✓ | ✓ |
| Admin Panel | ✗ | ✓ |
| Register Users | ✗ | ✓ |
| WT Reports | ✗ | ✓ |
| Export | ✗ | ✓ |

### Data Protection

- **Soft Delete**: Data preserved for audit, never physically deleted
- **Input Validation**: Tag normalization, length checks
- **Physical Security**: SQLite database unencrypted (assumes secure deployment location)

---

## Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Single DB connection | No concurrent writes | SQLite handles locking |
| No WAL mode | Reduced crash resilience | Explicit commits after writes |
| Clock drift | Inaccurate timestamps | Use NTP on host system |
| Single instance | No multi-terminal | Design as kiosk appliance |
| No authentication PIN | Physical access = admin | Deploy in secure location |

---

*Last updated: Dec 2025*

