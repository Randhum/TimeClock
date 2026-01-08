# TimeClock

> **RFID-Based Employee Time Tracking System**

A production-ready kiosk application for workforce time tracking, built with **Python**, **Kivy**, and **SQLite**. Designed for touch-screen environments with RFID badge readers.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Launch application
python -m src.main
```

On first launch, you'll be prompted to register an **administrator**. This step cannot be skipped.

---

## Features

- 🏷️ **RFID Badge Authentication** - Quick clock in/out with badge scan
- 📊 **Working Time Reports** - Per-employee reports with daily/weekly/monthly breakdowns
- 📱 **Touch-Optimized Interface** - Designed for touchscreen kiosks
- 💾 **Local SQLite Database** - No cloud dependency, all data stored locally
- 📤 **Multiple Export Formats** - Export raw entries (CSV) or formatted working hours reports (Excel, CSV, PDF)
- 🔒 **Role-Based Access** - Admin and Employee roles with appropriate permissions
- 🤖 **Screensaver** - Matrix-style screensaver activates after 60s idle
- 💬 **Greeter Messages** - Customizable welcome/goodbye messages
- 🛡️ **Robust Data Integrity** - Atomic transactions, employee-level locking, and comprehensive error handling

---

## System Requirements

### Hardware

- Raspberry Pi 3B+ or higher (recommended) or any Linux system
- Touch display (800×480 minimum)
- RFID reader: RFIDeas pcProx or compatible HID device

**Tested Hardware:**
- Raspberry Pi 3 Model B+
- Official Raspberry Pi Touch Display (7")
- RFIDeas pcProx Plus (RDR-80582AKU)

### Software

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | ≥3.8 | Runtime |
| Kivy | ≥2.0 | GUI framework |
| Peewee | ≥3.15 | ORM for SQLite |
| hidapi | ≥0.12 | RFID communication |
| openpyxl | ≥3.0 | Excel file generation |
| reportlab | ≥3.6 | PDF generation |

---

## Documentation

- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** - Complete guide for end users and administrators [IT](docs/USER_GUIDE_IT.md), [DE](docs/USER_GUIDE_DE.md)
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical documentation for developers

---


## Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-org/TimeClock.git
cd TimeClock
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. First Run

```bash
python -m src.main
```

On first launch, you'll be prompted to register an **administrator**. This step cannot be skipped.

---

## Configuration

### Custom Greeting Messages

Customize messages displayed when employees clock in/out by editing text files in `src/data/greetings/`:

- **Shift-specific files**: `greetings_in_morning_de.txt`, `greetings_out_evening_ch.txt`, etc.
- **Format**: `greetings_{in|out}_{morning|midday|evening}_{ch|de|it|rm}.txt`
- **Languages**: `ch` (Schweizerdeutsch), `de` (Deutsch), `it` (Italienisch), `rm` (Rätoromanisch)
- **Fallback files**: `greetings_in.txt`, `greetings_out.txt`
- **Placeholders**: Use `[Name]` to insert employee's first name

**Shift Selection:**
- **Morning**: 04:00 - 11:00
- **Midday**: 11:00 - 17:00
- **Evening**: 17:00 - 04:00
- In overlapping time ranges (e.g., 10:00-14:00), the system randomly selects from applicable shifts
- The selected greeting file matches the clock action (`in` or `out`) and is randomly chosen from the appropriate time-based shift

### Export Directory

By default, exports are saved to `./exports/`. Override with an environment variable:

```bash
export TIME_CLOCK_EXPORT_PATH=/mnt/usb
python -m src.main
```

**Auto-Detection**: The system scans `/media`, `/run/media`, and `/mnt` for mounted USB drives and uses them automatically.

### Working Hours Export

TimeClock supports exporting working hours reports in multiple formats, organized by employee and month.

#### Features

- **Excel Export** - Structured Excel file with hours per day per month
- **CSV Export** - Semicolon-delimited CSV for import into other systems
- **PDF Export** - Formatted PDF report for printing and archiving (landscape A4)
- **All Employees LGAV Report** - Single Excel file with one sheet per employee for the last year

#### Usage

**Individual Employee Reports:**
1. Navigate to **Admin → Work Time Reports**
2. Select an employee and date range
3. Choose export format:
   - **Excel** - For spreadsheet applications
   - **CSV** - For import into payroll/accounting systems
   - **PDF** - For printing and documentation

**All Employees LGAV Report:**
1. Navigate to **Admin → LGAV Report (Alle Mitarbeiter)**
2. The system automatically generates an Excel file with:
   - One sheet per active employee
   - Last year's data (365 days from today)
   - Same format as individual reports
3. File is saved to the export directory with format: `LGAV_Alle_Mitarbeiter_YYYYMMDD_YYYYMMDD.xlsx`

#### Format Details

The export shows logged working hours per day, organized by month. Hours are calculated from actual clock in/out entries (TimeEntry records) in the database.

**Example Output:**

```
Arbeitszeitnachweis: Max Mustermann
Zeitraum: 01.12.2025 - 31.12.2025

Dezember 2025
1  | 2  | 3  | 4  | ... | 31 | Total
8:30|7:45|8:15|   | ... |8:00| 168:30

Januar 2026
1  | 2  | 3  | ... | 31 | Total
...
```

**Format Structure:**
- **Header**: Employee name and date range
- **Month Section**: Month name and year (e.g., "Dezember 2025")
- **Day Row**: Day numbers (1-31) across columns
- **Hours Row**: Working hours in H:MM format per day (calculated from clock entries)
- **Total Column**: Monthly total hours in H:MM format

**Data Source:**
- Hours are calculated from actual `TimeEntry` records (clock in/out timestamps)
- Each day shows the sum of all work sessions for that day
- Days without clock entries show as empty
- Multiple clock in/out pairs per day are automatically summed
- **Sessions spanning midnight**: If an employee clocks in before midnight and clocks out after midnight, the session is correctly matched and counted on the day the clock-in occurred

#### Requirements

Export requires additional dependencies:
```bash
pip install openpyxl reportlab
```

These are included in `requirements.txt` and installed automatically.

### Editing Time Entries

When editing time entries (adding or deleting entries):

- **Automatic Action Determination**: The system automatically determines whether an entry should be "IN" or "OUT" based on the chronological order of entries. You no longer need to manually select the action when adding entries.
- **Action Recalculation**: When entries are added, deleted, or modified, all remaining entries have their actions automatically recalculated to maintain proper IN/OUT alternation.
- **Session Matching**: Work sessions are matched chronologically across day boundaries. If you clock in before midnight and clock out after midnight, the session is correctly linked and counted on the day you clocked in.

### RFID Provider

The application automatically detects RFID hardware. If unavailable, it falls back to a mock provider for development:

```python
# src/main.py - Force mock mode for testing
self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=True)
```

---

## Deployment

### Production Setup on Raspberry Pi

For production deployments, TimeClock should run as a systemd service that starts automatically on boot.

#### Prerequisites

1. Complete installation (including virtual environment)
2. Desktop environment enabled (required for Kivy display)
3. User permissions for USB devices and display

#### Step 1: Configure USB/RFID Permissions

Add your user to the `plugdev` group to access USB devices:

```bash
sudo usermod -a -G plugdev $USER
```

**Optional**: Create a udev rule for persistent RFID reader access:

```bash
sudo nano /etc/udev/rules.d/99-rfid-reader.rules
```

Add (adjust vendor ID for your device):

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0c27", MODE="0666", GROUP="plugdev"
```

Reload udev rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### Step 2: Create Systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/timeclock.service
```

**Service Configuration** (adjust paths for your environment):

```ini
[Unit]
Description=TimeClock RFID Time Tracking Application
After=graphical.target network.target
Wants=graphical.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/TimeClock
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/pi/.Xauthority"
Environment="HOME=/home/pi"
Environment="PATH=/usr/bin:/usr/local/bin:/home/pi/.local/bin"
ExecStart=/home/pi/TimeClock/venv/bin/python -m src.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=graphical.target
```

**Configuration Notes:**

- **`User`/`Group`**: Replace `pi` with your actual username
- **`WorkingDirectory`**: Absolute path to your TimeClock project directory
- **`ExecStart`**: Path to Python in your virtual environment (`venv/bin/python`)
- **`RestartSec`**: Delay before restarting after failure (10 seconds)
- **`WantedBy=graphical.target`**: Ensures service starts after desktop is ready

#### Step 3: Enable and Start Service

Reload systemd and enable the service:

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service (starts on boot)
sudo systemctl enable timeclock.service

# Start service immediately
sudo systemctl start timeclock.service

# Verify status
sudo systemctl status timeclock.service
```

#### Step 4: Verify Service Operation

Check service logs:

```bash
# View live logs
sudo journalctl -u timeclock.service -f

# View last 50 log entries
sudo journalctl -u timeclock.service -n 50

# View logs since boot
sudo journalctl -u timeclock.service -b
```

Expected log output should show:
- Application initialization
- RFID provider connection status
- Database connection established
- Screen transitions

#### Service Management Commands

| Command | Purpose |
|---------|---------|
| `sudo systemctl start timeclock.service` | Start the service |
| `sudo systemctl stop timeclock.service` | Stop the service |
| `sudo systemctl restart timeclock.service` | Restart the service |
| `sudo systemctl status timeclock.service` | Check service status |
| `sudo systemctl enable timeclock.service` | Enable auto-start on boot |
| `sudo systemctl disable timeclock.service` | Disable auto-start |
| `sudo journalctl -u timeclock.service -f` | Follow live logs |

#### Troubleshooting Deployment Issues

**Service fails to start:**

```bash
# Check detailed error logs
sudo journalctl -u timeclock.service -n 100 --no-pager

# Verify paths in service file
cat /etc/systemd/system/timeclock.service

# Test manual execution
cd /home/pi/TimeClock
source venv/bin/activate
python -m src.main
```

**Display not available:**

- Ensure desktop autologin is enabled: `sudo raspi-config` → Boot Options → Desktop Autologin
- Verify display: `echo $DISPLAY` (should output `:0`)
- Check X server: `ps aux | grep Xorg`

**RFID device not detected:**

- Verify USB connection: `lsusb`
- Check permissions: `ls -l /dev/bus/usb/`
- Ensure user is in `plugdev` group: `groups $USER`
- Test manually: `python -c "from src.rfid import get_rfid_provider; print(get_rfid_provider(lambda x: None))"`

**Service restarts continuously:**

- Check application logs for Python errors
- Verify database file permissions: `ls -l /home/pi/TimeClock/*.db`
- Ensure virtual environment is complete: `ls -l venv/bin/python`

#### Disabling/Removing Service

To stop and disable the service:

```bash
sudo systemctl stop timeclock.service
sudo systemctl disable timeclock.service
sudo rm /etc/systemd/system/timeclock.service
sudo systemctl daemon-reload
```

---

## Project Structure

```
TimeClock/
├── src/
│   ├── main.py                    # Application entry point
│   │
│   ├── services/                 # Business logic layer
│   │   ├── clock_service.py      # Clock in/out logic
│   │   ├── state_service.py      # State management
│   │   ├── popup_service.py      # Popup management
│   │   └── report_service.py     # Report generation engine
│   │
│   ├── presentation/             # UI layer
│   │   ├── timeclock.kv          # UI layout definitions
│   │   ├── screens/              # Screen controllers
│   │   ├── popups/               # Popup components
│   │   └── widgets/              # Custom widgets
│   │
│   ├── hardware/                 # Hardware layer
│   │   ├── rfid.py               # RFID hardware abstraction
│   │   ├── pcprox.py             # RFID reader driver
│   │   ├── configure.py          # Hardware configuration
│   │   └── usbtest.py            # USB testing utilities
│   │
│   ├── data/                     # Data layer
│   │   ├── database.py           # Data models and queries
│   │   └── greetings/            # Greeting message files
│   │
│   └── utils/                    # Utilities
│       ├── errors.py             # Error classes
│       └── export_utils.py       # Export utilities
│
├── scripts/                      # Utility scripts
│   ├── migrate_db.py             # Database migration script
│   ├── list_employee_entries.py  # List clock entries for an employee
│   ├── delete_entry.py           # Delete a clock entry by ID and recalculate actions
│   └── change_employee_name.py   # Change an employee's name
├── exports/                      # Default export directory
├── requirements.txt
└── README.md
```

---

## Utility Scripts

### List Employee Clock Entries

The `scripts/list_employee_entries.py` script allows you to list all clock entries for a specific employee from the command line.

**Usage:**

```bash
# List entries by employee name (partial match)
python scripts/list_employee_entries.py --name "John Doe"

# List entries by RFID tag
python scripts/list_employee_entries.py --tag "ABCD1234"

# Interactive mode - list all employees and select one
python scripts/list_employee_entries.py --all
```

**Output:**
- Displays all clock entries (IN/OUT) for the selected employee
- Shows entry ID, timestamp, action, and status
- Entries are sorted by timestamp (newest first)

**Note:** If the database is encrypted, ensure `TIMECLOCK_ENV_KEY` environment variable is set before running the script.

### Delete Clock Entry

The `scripts/delete_entry.py` script allows you to soft-delete a clock entry by ID and automatically recalculate all following actions for that employee.

**Usage:**

```bash
# Delete entry by ID with employee name verification
python scripts/delete_entry.py --id 431 --name "John Doe"

# Delete entry by ID with RFID tag verification
python scripts/delete_entry.py --id 408 --tag "ABCD1234"

# Force delete without verification (use with caution)
python scripts/delete_entry.py --id 431 --force
```

**Features:**
- Verifies the entry belongs to the specified employee (unless `--force` is used)
- Soft-deletes the entry (sets `active=False`)
- Automatically recalculates all remaining active entries for that employee
- Ensures proper IN/OUT alternation after deletion
- Shows which entries were updated during recalculation

**Output:**
- Displays entry information before deletion
- Prompts for confirmation (unless `--force` is used)
- Shows which subsequent entries had their actions updated
- Provides summary of changes made

**Note:** If the database is encrypted, ensure `TIMECLOCK_ENV_KEY` environment variable is set before running the script.

### Change Employee Name

The `scripts/change_employee_name.py` script allows you to change an employee's name.

**Usage:**

```bash
# Change name by current name
python scripts/change_employee_name.py --name "John Doe" --new-name "John Smith"

# Change name by RFID tag
python scripts/change_employee_name.py --tag "ABCD1234" --new-name "Jane Doe"

# Interactive mode - list all employees and select one
python scripts/change_employee_name.py --all
```

**Features:**
- Find employee by name (partial match) or RFID tag
- Interactive mode to select from all employees
- Validates new name (not empty, max 100 characters)
- Shows current employee information before change
- Confirms change before applying (unless `--new-name` is provided)
- Updates the name in the database

**Output:**
- Displays current employee information
- Shows old and new name
- Confirms successful update

**Note:** If the database is encrypted, ensure `TIMECLOCK_ENV_KEY` environment variable is set before running the script.

### Database Migration

The `scripts/migrate_db.py` script migrates an unencrypted database to SQLCipher encrypted format. See the script's help for usage:

```bash
python scripts/migrate_db.py --help
```

---

## Development

### Running with Mock RFID

For development without hardware:

```python
# In src/main.py, change:
self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=True)
```

### Logging

Debug logging is enabled by default:

```python
logging.basicConfig(level=logging.DEBUG)
```

---

## Reliability & Data Integrity

The application includes comprehensive reliability features to ensure data integrity and prevent corruption:

### Atomic Operations
- **Clock Operations**: Action determination and entry creation happen atomically in a single transaction, preventing race conditions
- **Manual Entries**: All manual entry operations use transactions with proper rollback on errors
- **Entry Deletions**: Soft-delete operations are wrapped in transactions with explicit commits

### Employee-Level Locking
- **Concurrent Modification Protection**: Each employee has a dedicated lock to prevent simultaneous modifications to their time entries
- **Thread-Safe Operations**: All database operations for the same employee are serialized to prevent data corruption

### Action Validation
- **Real-Time Validation**: Actions are validated against current database state at save time, not just at UI time
- **Smart Recalculation**: Action recalculation only occurs when logical errors are detected (e.g., two consecutive 'in' actions)
- **Preservation of Valid Data**: Existing valid action patterns are preserved during recalculation

### Database Error Handling
- **Retry Logic**: Automatic retry with exponential backoff for transient database errors (locked, busy, timeout)
- **Connection Recovery**: Robust connection management with automatic reconnection on failures
- **Transaction Rollback**: All operations include proper error handling with transaction rollback on failures

### Data Validation
- **Timestamp Validation**: Prevents entries with unreasonable dates (more than 1 day in future or 1 year in past)
- **Action Validation**: Ensures all actions are valid ('in' or 'out') before database operations
- **Employee Validation**: Verifies employee is active before allowing time entry creation

### Error Recovery
- **Graceful Degradation**: Operations continue even if non-critical steps fail (e.g., recalculation)
- **Comprehensive Logging**: All errors are logged with context for debugging
- **User Feedback**: Clear error messages inform users of issues without exposing technical details

---

## Troubleshooting

### RFID Not Detected

**Problem**: "Falling back to MockRFIDProvider"

**Solution**:
1. Check USB connection
2. Verify permissions: `sudo usermod -a -G plugdev $USER`
3. Create udev rule for device

### Database Locked

**Problem**: "Database is locked" errors

**Solution**:
1. Ensure only one instance is running
2. Check for crashed background processes: `ps aux | grep python`

### Export Fails

**Problem**: Cannot write export file

**Solution**:
1. Check directory permissions
2. Verify USB is mounted read-write
3. Set custom path: `export TIME_CLOCK_EXPORT_PATH=/path/to/dir`

---

## Credits

This project was inspired by [RPI TimeClock Terminal](https://github.com/niclasku/rpi-timeclock-terminal) from [niclasku](https://github.com/niclasku).

---


## License 

MIT License. See [LICENSE](LICENSE) for details.





