# TimeClock — Technical Architecture & Flow Analysis

> Comprehensive documentation of internal system behavior, data flows, and implementation details.

---

## Document Purpose

This document provides a deep-dive into the TimeClock application architecture for:

- **Developers** extending or maintaining the codebase
- **System Integrators** connecting TimeClock to external systems
- **QA Engineers** designing test strategies
- **Operations** teams deploying and troubleshooting

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Application Lifecycle](#2-application-lifecycle)
3. [RFID Subsystem](#3-rfid-subsystem)
4. [Screen Controllers](#4-screen-controllers)
5. [Database Layer](#5-database-layer)
6. [Working Time Report Engine](#6-working-time-report-engine)
7. [Export Subsystem](#7-export-subsystem)
8. [Input Handling](#8-input-handling)
9. [Error Handling Strategy](#9-error-handling-strategy)
10. [Testing Strategy](#10-testing-strategy)
11. [Performance Considerations](#11-performance-considerations)
12. [Security Model](#12-security-model)
13. [Known Limitations](#13-known-limitations)
14. [Appendix: Sequence Diagrams](#appendix-sequence-diagrams)

---

## 1. System Architecture

### 1.1 Component Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                      Kivy UI (timeclock.kv)                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │TimeClock │ │  Admin   │ │ Register │ │ WTReport │  ...     │  │
│  │  │  Screen  │ │  Screen  │ │  Screen  │ │  Screen  │          │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │  │
│  └───────┼────────────┼────────────┼────────────┼────────────────┘  │
│          │            │            │            │                    │
│          └────────────┴─────┬──────┴────────────┘                    │
│                             ▼                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                   Screen Manager (main.py)                     │  │
│  │            Event Routing • State Management • Popups           │  │
│  └────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────────┐
│                         BUSINESS LAYER                               │
│                               ▼                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Clock Logic   │    │  Report Engine  │    │  Export Utils   │  │
│  │                 │    │  (wt_report.py) │    │(export_utils.py)│  │
│  │ • Toggle IN/OUT │    │                 │    │                 │  │
│  │ • Session Mgmt  │    │ • FIFO Pairing  │    │ • USB Detection │  │
│  │ • Validation    │    │ • Aggregation   │    │ • Path Resolve  │  │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘  │
│           │                      │                      │            │
└───────────┼──────────────────────┼──────────────────────┼────────────┘
            │                      │                      │
┌───────────┼──────────────────────┼──────────────────────┼────────────┐
│           │              DATA LAYER                     │            │
│           ▼                      ▼                      ▼            │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    Peewee ORM (database.py)                     │ │
│  │         Models: Employee, TimeEntry • Atomic Transactions       │ │
│  └───────────────────────────────┬─────────────────────────────────┘ │
│                                  ▼                                   │
│                       ┌─────────────────────┐                        │
│                       │   SQLite Database   │                        │
│                       │   (timeclock.db)    │                        │
│                       └─────────────────────┘                        │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                         HARDWARE LAYER                               │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   RFID Provider (rfid.py)                       │ │
│  │                                                                 │ │
│  │  ┌─────────────────────┐      ┌─────────────────────┐          │ │
│  │  │ PcProxRFIDProvider  │  OR  │  MockRFIDProvider   │          │ │
│  │  │   (Real Hardware)   │      │   (Development)     │          │ │
│  │  └──────────┬──────────┘      └──────────┬──────────┘          │ │
│  │             │                            │                      │ │
│  │             ▼                            ▼                      │ │
│  │  ┌─────────────────────┐      ┌─────────────────────┐          │ │
│  │  │   USB HID Device    │      │   Simulated Input   │          │ │
│  │  │   (pcProx Reader)   │      │                     │          │ │
│  │  └─────────────────────┘      └─────────────────────┘          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Threading Model

| Thread | Purpose | Communication |
|--------|---------|---------------|
| **Main Thread** | Kivy event loop, UI rendering | Direct method calls |
| **RFID Thread** | HID polling, tag detection | `Clock.schedule_once()` → Main |
| **DB Thread** | N/A (synchronous Peewee) | Blocking calls from Main |

**Thread Safety**: RFID callbacks are scheduled on the main thread via Kivy's `Clock`, ensuring all UI and database operations run single-threaded.

---

## 2. Application Lifecycle

### 2.1 Startup Sequence

```
TimeClockApp.run()
        │
        ▼
┌───────────────────────────────────────┐
│            build()                    │
├───────────────────────────────────────┤
│ 1. Configure logging (DEBUG)         │
│ 2. Set keyboard mode → 'dock'         │
│ 3. initialize_db() → Create tables    │
│ 4. get_rfid_provider()               │
│    ├─ Try: PcProxRFIDProvider        │
│    └─ Fallback: MockRFIDProvider     │
│ 5. rfid.start() → Background thread   │
│ 6. Builder.load_file('timeclock.kv')  │
│ 7. check_initial_setup()             │
│    └─ If no admin → force register    │
└───────────────────────────────────────┘
        │
        ▼
    Event Loop
        │
        ▼ (on exit)
┌───────────────────────────────────────┐
│           on_stop()                   │
├───────────────────────────────────────┤
│ 1. rfid.stop() → Signal thread exit   │
│ 2. close_db() → Cleanup connection    │
└───────────────────────────────────────┘
```

### 2.2 First-Run Behavior

When `get_admin_count() == 0`:

1. Navigation to all screens except `register` is blocked
2. Admin checkbox is forced `True` and disabled
3. Cancel button is hidden
4. User must complete admin registration to proceed

---

## 3. RFID Subsystem

### 3.1 Provider Architecture

```python
class RFIDProvider(ABC):
    """Abstract base class for RFID readers"""
    
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback      # Tag detected → callback(tag_id)
        self._running = False
        self._thread = None
        self._command_queue = Queue()  # For LED control commands
    
    @abstractmethod
    def _loop(self): ...              # Polling implementation
    
    def start(self): ...              # Start background thread
    def stop(self): ...               # Signal thread termination
    def signal_success(self): ...     # Queue green LED command
    def signal_error(self): ...       # Queue red LED command
```

### 3.2 Scan Deduplication

To prevent duplicate clock entries from rapid scans:

```python
# In TimeClockApp
_recent_scan_times: Dict[str, float] = {}
SCAN_DEBOUNCE_SECONDS = 1.2

def handle_scan(self, tag_id: str):
    now = time.time()
    last_scan = self._recent_scan_times.get(tag_id, 0)
    
    if now - last_scan < SCAN_DEBOUNCE_SECONDS:
        logger.debug(f"Ignoring duplicate scan: {tag_id}")
        return
    
    self._recent_scan_times[tag_id] = now
    # ... proceed with normal handling
```

### 3.3 LED Feedback Protocol

| Signal | LED Pattern | Meaning |
|--------|-------------|---------|
| Success | Green flash (500ms) | Clock action recorded |
| Error | Red blink × 3 | Invalid tag or operation failed |
| Ready | Green steady | Reader connected and ready |

---

## 4. Screen Controllers

### 4.1 Screen Navigation Map

```
                    ┌─────────────┐
                    │  TimeClock  │ ◄─── Default/Home
                    │   Screen    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │ Admin Tag       │ Unknown Tag     │ Employee Tag
         ▼                 ▼                 ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Admin    │    │   Popup:    │    │ Clock Action│
│   Screen    │    │ "Unknown"   │    │  + Summary  │
└──────┬──────┘    └─────────────┘    └─────────────┘
       │
       ├────────────────┬─────────────────┬────────────────┐
       ▼                ▼                 ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Register   │  │  Identify   │  │  WT Report  │  │ Export CSV  │
│   Screen    │  │   Screen    │  │   Screen    │  │   Action    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

### 4.2 TimeClockScreen Behavior

**State Properties:**
- `status_message: StringProperty` — Current status text
- `show_today_buttons: BooleanProperty` — Controls action button visibility
- `last_clocked_employee: ObjectProperty` — Reference for summary/edit

**Clock Action Flow:**

```
Badge Scan
    │
    ▼
┌──────────────────────────────┐
│ get_employee_by_tag(tag_id)  │
└──────────────┬───────────────┘
               │
    ┌──────────┴──────────┐
    │ None                │ Employee
    ▼                     ▼
┌─────────────┐    ┌──────────────────────────┐
│ Popup:      │    │ TimeEntry.get_last(emp)  │
│ "Unknown"   │    └────────────┬─────────────┘
└─────────────┘                 │
                                ▼
                    ┌───────────────────────────┐
                    │ Determine action:         │
                    │ last='in' → action='out'  │
                    │ else     → action='in'    │
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────┐
                    │ create_time_entry(emp,act)│
                    └────────────┬──────────────┘
                                 │
                                 ▼
                    ┌───────────────────────────┐
                    │ Update status_message     │
                    │ Reveal today buttons (5s) │
                    │ Signal LED success        │
                    └───────────────────────────┘
```

### 4.3 RegisterScreen Behavior

**Validation Rules:**
1. Name: Non-empty, trimmed
2. Tag: ≥4 characters, uppercase
3. Tag: Not already registered (IntegrityError on conflict)
4. First user: Must be admin

**Registration Flow:**

```
User Input (Name)
    │
    ▼
Badge Scan → tag_id property set
    │
    ▼
Save Button → save_user()
    │
    ├─ Validate inputs
    │
    ├─ create_employee(name, tag, is_admin)
    │       │
    │       ├─ Atomic transaction
    │       ├─ Employee.create()
    │       └─ Return employee or raise IntegrityError
    │
    ├─ On Success:
    │       ├─ Navigate to Admin
    │       ├─ Show success popup
    │       └─ Signal LED success
    │
    └─ On IntegrityError:
            ├─ Show error popup
            └─ Signal LED error
```

---

## 5. Database Layer

### 5.1 Connection Management

```python
def ensure_db_connection():
    """Ensure database connection is open and valid"""
    if db.is_closed():
        db.connect(reuse_if_open=True)
```

Called before every database operation to handle connection drops.

### 5.2 Transaction Model

All write operations use atomic transactions:

```python
def create_time_entry(employee: Employee, action: str) -> TimeEntry:
    ensure_db_connection()
    with db.atomic():
        entry = TimeEntry.create(
            employee=employee,
            action=action,
            timestamp=datetime.datetime.now(),
            active=True
        )
    db.commit()  # Explicit commit for durability
    return entry
```

### 5.3 Soft Delete Pattern

Entries are never physically deleted. Instead:

```python
def soft_delete_time_entries(entry_ids: List[int]) -> int:
    """Mark entries as inactive"""
    ensure_db_connection()
    with db.atomic():
        count = (TimeEntry
                 .update(active=False)
                 .where(TimeEntry.id.in_(entry_ids))
                 .execute())
    db.commit()
    return count
```

All queries filter by `active=True`:

```python
TimeEntry.select().where(
    TimeEntry.employee == employee,
    TimeEntry.active == True
)
```

### 5.4 Query Patterns

| Query | Purpose | Filter |
|-------|---------|--------|
| `get_employee_by_tag(tag)` | Lookup employee | `active=True` |
| `get_all_employees()` | List for selection | `active=True` (default) |
| `TimeEntry.get_last_for_employee(emp)` | Determine next action | `active=True` |
| `get_time_entries_for_export()` | Raw export | `active=True` |

---

## 6. Working Time Report Engine

### 6.1 Session Pairing Algorithm (FIFO)

The report engine uses a **queue-based FIFO** algorithm to pair clock-in and clock-out events:

```python
from collections import deque

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

### 6.2 Example: FIFO Pairing

```
Input Entries (Day: 2024-01-15)
───────────────────────────────
08:00  IN   (id=1)
08:01  IN   (id=2)   ← Duplicate scan
12:00  OUT  (id=3)
12:01  OUT  (id=4)   ← Duplicate scan
13:00  IN   (id=5)
17:00  OUT  (id=6)

Queue State Progression
───────────────────────
After 08:00 IN:  [(08:00, 1)]
After 08:01 IN:  [(08:00, 1), (08:01, 2)]
After 12:00 OUT: [(08:01, 2)]           → Session 1: 08:00-12:00
After 12:01 OUT: []                     → Session 2: 08:01-12:01 (duplicate)
After 13:00 IN:  [(13:00, 5)]
After 17:00 OUT: []                     → Session 3: 13:00-17:00

Resulting Sessions
──────────────────
Session 1:  08:00 → 12:00  (4h 00m)  IDs: 1, 3
Session 2:  08:01 → 12:01  (4h 00m)  IDs: 2, 4  ← Can be soft-deleted
Session 3:  13:00 → 17:00  (4h 00m)  IDs: 5, 6
```

### 6.3 Report Output Formats

**Text Format** (`to_text()`):

```
Working Time Report for: John Smith
Period: 2024-01-01 to 2024-01-31
Generated: 2024-01-31 18:00:00
========================================

2024-01-15 (Monday)
  08:00 → 12:00  [04:00]
  13:00 → 17:00  [04:00]
  Daily Total: 08:00

----------------------------------------
SUMMARY
  Total Days Worked: 22
  Total Hours: 176:00
  Average per Day: 08:00
========================================
```

**CSV Format** (`to_csv()`):

```csv
Date,Clock In,Clock Out,Duration (HH:MM)
2024-01-15,08:00,12:00,04:00
2024-01-15,13:00,17:00,04:00
```

---

## 7. Export Subsystem

### 7.1 USB Detection Logic

```python
def get_export_directory() -> Path:
    """Find best export destination"""
    
    # 1. Check environment override
    if 'TIME_CLOCK_EXPORT_PATH' in os.environ:
        return Path(os.environ['TIME_CLOCK_EXPORT_PATH'])
    
    # 2. Scan for USB mounts
    usb_roots = ['/media', '/run/media', '/mnt']
    for root in usb_roots:
        if Path(root).exists():
            for mount in Path(root).iterdir():
                if mount.is_dir() and os.access(mount, os.W_OK):
                    return mount
    
    # 3. Fallback to local exports/
    return Path('exports')
```

### 7.2 Export File Naming

| Export Type | Pattern |
|-------------|---------|
| Raw Entries | `TimeEntries_YYYYMMDD_HHMMSS.csv` |
| WT Report | `WT_Report_<Name>_<StartDate>_to_<EndDate>.csv` |

---

## 8. Input Handling

### 8.1 Double-Keystroke Filtering

Touch keyboards on some devices send duplicate keystrokes. The `FilteredTextInput` class mitigates this:

```python
class FilteredTextInput(TextInput):
    """Filters every other keystroke to prevent double-typing"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._input_counter = 0
    
    def insert_text(self, substring, from_undo=False):
        if from_undo:
            return super().insert_text(substring, from_undo)
        
        # Paste operations (len > 1) bypass filter
        if len(substring) > 1:
            self._input_counter = 0
            return super().insert_text(substring, from_undo)
        
        # Filter every other character
        self._input_counter += 1
        if self._input_counter % 2 == 0:
            return  # Skip this character
        
        return super().insert_text(substring, from_undo)
    
    def on_focus(self, instance, value):
        if value:  # Reset on focus gain
            self._input_counter = 0
    
    def do_backspace(self, from_undo=False, mode='bkspc'):
        self._input_counter = 0  # Reset on backspace
        return super().do_backspace(from_undo, mode)
```

---

## 9. Error Handling Strategy

### 9.1 Error Categories

| Category | Handling | User Feedback |
|----------|----------|---------------|
| **Database** | Rollback + Retry | Popup with message |
| **RFID** | Fallback to Mock | Silent (logs only) |
| **Validation** | Block operation | Popup with guidance |
| **Export** | Fail gracefully | Popup with error |

### 9.2 Exception Flow

```
Exception Raised
       │
       ▼
┌──────────────────────┐
│ Log at ERROR level   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Rollback transaction │  (if in db.atomic())
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Show user popup      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Signal LED error     │
└──────────────────────┘
```

---

## 10. Testing Strategy

### 10.1 Unit Test Coverage

| Module | Focus Areas |
|--------|-------------|
| `database.py` | CRUD operations, constraints, soft delete |
| `wt_report.py` | FIFO pairing, edge cases, calculations |
| `export_utils.py` | USB detection, path resolution |

### 10.2 Integration Tests

| Flow | Test Cases |
|------|------------|
| Registration | Valid data, duplicate tag, first admin |
| Clock Action | IN/OUT toggle, rapid scans, unknown tag |
| Reports | Date ranges, open sessions, empty data |
| Export | USB present, USB absent, permissions |

### 10.3 Test Checklist

**Functional:**
- [ ] First run forces admin creation
- [ ] Employee registration with valid data
- [ ] Duplicate tag rejection
- [ ] Clock IN/OUT alternation
- [ ] Admin badge → admin screen
- [ ] CSV export with data
- [ ] CSV export with no data
- [ ] WT report generation
- [ ] Session soft-delete

**Edge Cases:**
- [ ] Rapid RFID scans (debounce)
- [ ] Power loss during write
- [ ] RFID disconnect/reconnect
- [ ] Invalid date range in reports
- [ ] USB removed during export

**UI:**
- [ ] Keyboard double-typing fixed
- [ ] Screen navigation
- [ ] Popup display/dismiss
- [ ] ScrollView behavior

---

## 11. Performance Considerations

### 11.1 Database

- **Index Usage**: `rfid_tag` and `timestamp` are indexed
- **Query Optimization**: Queries filter early with `WHERE` clauses
- **Connection Reuse**: Single connection, ensured before each operation

### 11.2 UI

- **Lazy Loading**: Employee lists populated on screen enter
- **Debouncing**: RFID scans debounced at 1.2s
- **Scheduled Updates**: UI updates via `Clock.schedule_once()`

### 11.3 Memory

- **Report Generation**: Processes entries in batches by day
- **Export**: Streams to file, doesn't hold full dataset in memory

---

## 12. Security Model

### 12.1 Access Control

| Resource | Employee | Admin |
|----------|----------|-------|
| Clock In/Out | ✓ | ✓ |
| View Own Summary | ✓ | ✓ |
| Edit Own Sessions | ✓ | ✓ |
| Admin Panel | ✗ | ✓ |
| Register Users | ✗ | ✓ |
| WT Reports | ✗ | ✓ |
| Export | ✗ | ✓ |

### 12.2 Data Protection

- **No Encryption**: SQLite database is unencrypted (physical security assumed)
- **Soft Delete**: Data preserved for audit, never physically deleted
- **Input Validation**: Tag normalization, length checks

---

## 13. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Single DB connection | No concurrent writes | SQLite handles locking |
| No WAL mode | Reduced crash resilience | Explicit commits after writes |
| Clock drift | Inaccurate timestamps | Use NTP on host system |
| Single instance | No multi-terminal | Design as kiosk appliance |
| No authentication PIN | Physical access = admin | Deploy in secure location |

---

## Appendix: Sequence Diagrams

### A.1 Clock Action Sequence

```
┌─────────┐    ┌───────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐
│  RFID   │    │ TimeClock │    │ Database │    │ WTReport │    │   UI   │
│ Reader  │    │    App    │    │          │    │          │    │        │
└────┬────┘    └─────┬─────┘    └────┬─────┘    └────┬─────┘    └───┬────┘
     │               │               │               │              │
     │ tag_detected  │               │               │              │
     │──────────────>│               │               │              │
     │               │               │               │              │
     │               │ get_employee  │               │              │
     │               │──────────────>│               │              │
     │               │               │               │              │
     │               │   employee    │               │              │
     │               │<──────────────│               │              │
     │               │               │               │              │
     │               │ get_last_entry│               │              │
     │               │──────────────>│               │              │
     │               │               │               │              │
     │               │  last_entry   │               │              │
     │               │<──────────────│               │              │
     │               │               │               │              │
     │               │ create_entry  │               │              │
     │               │──────────────>│               │              │
     │               │               │               │              │
     │               │   success     │               │              │
     │               │<──────────────│               │              │
     │               │               │               │              │
     │               │ generate(today)               │              │
     │               │──────────────────────────────>│              │
     │               │               │               │              │
     │               │      summary                  │              │
     │               │<──────────────────────────────│              │
     │               │               │               │              │
     │               │ update_status                 │              │
     │               │─────────────────────────────────────────────>│
     │               │               │               │              │
     │  led_success  │               │               │              │
     │<──────────────│               │               │              │
     │               │               │               │              │
```

### A.2 WT Report Generation

```
┌─────────┐    ┌───────────┐    ┌──────────┐    ┌──────────────┐
│  Admin  │    │ WTReport  │    │ Database │    │     UI       │
│         │    │   Screen  │    │          │    │              │
└────┬────┘    └─────┬─────┘    └────┬─────┘    └──────┬───────┘
     │               │               │                  │
     │ select_employee               │                  │
     │──────────────>│               │                  │
     │               │               │                  │
     │ generate_btn  │               │                  │
     │──────────────>│               │                  │
     │               │               │                  │
     │               │ get_entries   │                  │
     │               │──────────────>│                  │
     │               │               │                  │
     │               │   entries[]   │                  │
     │               │<──────────────│                  │
     │               │               │                  │
     │               │ FIFO_pair()   │                  │
     │               │───────┐       │                  │
     │               │       │       │                  │
     │               │<──────┘       │                  │
     │               │               │                  │
     │               │ aggregate()   │                  │
     │               │───────┐       │                  │
     │               │       │       │                  │
     │               │<──────┘       │                  │
     │               │               │                  │
     │               │ to_text()                        │
     │               │─────────────────────────────────>│
     │               │               │                  │
     │   report_displayed            │                  │
     │<─────────────────────────────────────────────────│
     │               │               │                  │
```

---

*Document Version: 2.0*  
*Last Updated: December 2024*
