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

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [System Requirements](#system-requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Architecture](#architecture)
7. [Database Schema](#database-schema)
8. [User Guide](#user-guide)
9. [Working Time Reports](#working-time-reports)
10. [Export & Data Management](#export--data-management)
11. [Development](#development)
12. [Troubleshooting](#troubleshooting)
13. [License](#license)

---

## Overview

TimeClock is a self-service time tracking terminal that enables employees to clock in and out using RFID badges. Built for reliability and simplicity, it's ideal for manufacturing floors, warehouses, offices, and any environment requiring accurate attendance records.

**Key Highlights:**

- 🏷️ RFID badge authentication
- 📊 Real-time working time reports
- 📱 Touch-optimized interface
- 💾 Local SQLite database
- 📤 CSV export functionality
- 🔒 Role-based access (Admin/Employee)

**Tested Hardware:**
- Raspberry Pi 3 Model B+
- Official Raspberry Pi Touch Display (7")
- RFIDeas pcProx Plus (RDR-80582AKU)

---

## Features

### Core Functionality

| Feature | Description |
|---------|-------------|
| **Clock In/Out** | Toggle attendance state with a single badge scan |
| **Session Tracking** | Automatic pairing of clock-in/out events into work sessions |
| **Working Time Reports** | Per-employee reports with daily/weekly/monthly breakdowns |
| **CSV Export** | Export raw entries or formatted reports for payroll integration |
| **Soft Delete** | Remove erroneous entries while preserving audit trail |

### Access Control

| Role | Capabilities |
|------|--------------|
| **Employee** | Clock in/out, view personal today summary |
| **Admin** | All employee capabilities + user management, reports, exports |

### User Experience

- **Today Summary**: Brief overlay after each clock action showing total hours worked
- **Quick Edit**: 5-second action window to view/edit sessions after clocking
- **Instant Feedback**: LED indicators confirm successful/failed operations
- **On-Screen Keyboard**: Full touch support for data entry

---

## System Requirements

### Hardware

- Raspberry Pi 3B+ or higher (recommended) or any Linux system
- Touch display (800×480 minimum)
- RFID reader: RFIDeas pcProx or compatible HID device

### Software

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | ≥3.8 | Runtime |
| Kivy | ≥2.0 | GUI framework |
| Peewee | ≥3.15 | ORM for SQLite |
| hidapi | ≥0.12 | RFID communication |

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

### RFID Provider

The application automatically detects RFID hardware. If unavailable, it falls back to a mock provider for development.

```python
# src/main.py - Force mock mode for testing
self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=True)
```

### Export Directory

By default, exports are saved to `./exports/`. Override with an environment variable:

```bash
export TIME_CLOCK_EXPORT_PATH=/mnt/usb
python -m src.main
```

**Auto-Detection**: The system scans `/media`, `/run/media`, and `/mnt` for mounted USB drives and uses them automatically.

### Keyboard Mode

The virtual keyboard is configured for docked mode (always visible when focused):

```python
# src/main.py
Config.set('kivy', 'keyboard_mode', 'dock')
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TimeClock Application                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    main.py  │  │ timeclock.kv│  │     wt_report.py    │  │
│  │             │  │             │  │                     │  │
│  │  App Logic  │◄─┤  UI Layout  │  │  Report Generation  │  │
│  │  Screens    │  │  Styling    │  │  CSV Export         │  │
│  └──────┬──────┘  └─────────────┘  └──────────┬──────────┘  │
│         │                                      │             │
│         ▼                                      ▼             │
│  ┌─────────────┐                    ┌─────────────────────┐  │
│  │  database.py│◄───────────────────┤   export_utils.py   │  │
│  │             │                    │                     │  │
│  │  Peewee ORM │                    │  USB Detection      │  │
│  │  SQLite DB  │                    │  Path Resolution    │  │
│  └──────┬──────┘                    └─────────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────┐                                             │
│  │   rfid.py   │                                             │
│  │             │                                             │
│  │  HID Reader │                                             │
│  │  Mock Mode  │                                             │
│  └─────────────┘                                             │
└─────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `main.py` | Application entry point, screen controllers, event routing |
| `timeclock.kv` | Declarative UI layout using Kivy language |
| `database.py` | Data models, queries, transaction management |
| `rfid.py` | RFID hardware abstraction, background polling |
| `wt_report.py` | Working time calculations, report formatting |
| `export_utils.py` | Export path resolution, USB detection |

---

## Database Schema

### Employee

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| `name` | VARCHAR(100) | NOT NULL |
| `rfid_tag` | VARCHAR(50) | UNIQUE, NOT NULL, INDEXED |
| `is_admin` | BOOLEAN | DEFAULT FALSE |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| `active` | BOOLEAN | DEFAULT TRUE |

### TimeEntry

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| `employee_id` | INTEGER | FOREIGN KEY → Employee |
| `timestamp` | DATETIME | NOT NULL, INDEXED |
| `action` | VARCHAR(10) | 'in' or 'out' |
| `active` | BOOLEAN | DEFAULT TRUE |

**Note**: The `active` column enables soft deletion—entries are hidden from reports without losing audit history.

---

## User Guide

### Initial Setup

1. Launch the application
2. Register the first administrator (mandatory)
3. Admin badge + PIN unlocks management functions

### Daily Workflow

```
Employee Scans Badge
        │
        ▼
┌───────────────────┐
│ System identifies │
│ employee by RFID  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐     ┌───────────────────┐
│ Last action: OUT? │─Yes─▶│ Create: CLOCK IN  │
└────────┬──────────┘     └───────────────────┘
         │ No
         ▼
┌───────────────────┐
│ Create: CLOCK OUT │
└───────────────────┘
```

### Admin Functions

Access the admin panel by scanning an admin badge:

- **Register User**: Add new employees with RFID badges
- **Identify Tag**: Scan any badge to see its assignment
- **WT Reports**: Generate per-employee working time reports
- **Export CSV**: Download raw time entries

### Today Summary

After each clock action, employees see a brief overlay:

- Total hours worked today
- Quick buttons to view/edit sessions (visible for 5 seconds)
- Useful for catching duplicate scans immediately

---

## Working Time Reports

### Session Pairing Algorithm

The system uses **FIFO (First-In-First-Out)** pairing to match clock events:

```
Entries (chronological):
  IN  08:00
  IN  08:01  ← duplicate scan
  OUT 12:00
  OUT 12:01  ← duplicate scan
  IN  13:00
  OUT 17:00

Resulting Sessions:
  Session 1: 08:00 → 12:00 (4h 00m)
  Session 2: 08:01 → 12:01 (4h 00m)  ← flagged as duplicate
  Session 3: 13:00 → 17:00 (4h 00m)
```

Duplicate sessions can be soft-deleted via the entry editor.

### Report Contents

- **Daily Breakdown**: Each day's sessions with start/end times
- **Duration Calculation**: Hours and minutes per session
- **Totals**: Daily subtotals, period grand total, daily average
- **Open Sessions**: Flagged if employee forgot to clock out

### Generating Reports

1. Navigate to **Admin → WT Reports**
2. Select an employee
3. (Optional) Set date range
4. Click **Generate Report**
5. (Optional) **Export to CSV** for payroll

---

## Export & Data Management

### Export Formats

| Export Type | Contents | Destination |
|-------------|----------|-------------|
| Raw Entries | All time entries with timestamps | `TimeEntries_YYYYMMDD.csv` |
| WT Report | Formatted working time report | `WT_Report_<Name>_<Range>.csv` |

### USB Auto-Export

When a USB drive is connected:

1. System detects mount points (`/media`, `/run/media`, `/mnt`)
2. Exports are written directly to the USB
3. Status popup confirms the file path

### Soft Delete

Erroneous entries (double scans) can be removed without losing history:

1. Clock action triggers → 5-second action window
2. Click **Edit Today's Sessions**
3. Select entries to remove
4. Entries marked `active=FALSE` in database
5. Excluded from all reports and calculations

---

## Development

### Project Structure

```
TimeClock/
├── src/
│   ├── __init__.py
│   ├── main.py          # Application entry point
│   ├── database.py      # Data layer
│   ├── rfid.py          # RFID abstraction
│   ├── wt_report.py     # Report generation
│   ├── export_utils.py  # Export utilities
│   └── timeclock.kv     # UI definitions
├── libraries/
│   └── pcprox.py        # Low-level RFID protocol
├── exports/             # Default export directory
├── tests/               # Test suite (future)
├── requirements.txt
└── README.md
```

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

Log output includes:
- RFID connection events
- Database operations
- Report generation status
- Export file paths

---

## Troubleshooting

### RFID Not Detected

```
PROBLEM: "Falling back to MockRFIDProvider"
SOLUTION: 
  1. Check USB connection
  2. Verify permissions: sudo usermod -a -G plugdev $USER
  3. Create udev rule for device
```

### Double Character Input

```
PROBLEM: Keyboard types each letter twice
SOLUTION: Built-in FilteredTextInput handles this automatically
```

### Database Locked

```
PROBLEM: "Database is locked" errors
SOLUTION:
  1. Ensure only one instance is running
  2. Check for crashed background processes: ps aux | grep python
```

### Export Fails

```
PROBLEM: Cannot write export file
SOLUTION:
  1. Check directory permissions
  2. Verify USB is mounted read-write
  3. Set custom path: export TIME_CLOCK_EXPORT_PATH=/path/to/dir
```

---

## Future Roadmap

- [ ] Overtime calculation and alerts
- [ ] Break time tracking
- [ ] REST API for payroll integration
- [ ] Multi-location support
- [ ] Biometric authentication option
- [ ] Mobile companion app

---

## Credits

This project is a fork of [RPI TimeClock Terminal](https://github.com/niclasku/rpi-timeclock-terminal) by [niclasku](https://github.com/niclasku).

---

## License

MIT License. See [LICENSE](LICENSE) for details.
