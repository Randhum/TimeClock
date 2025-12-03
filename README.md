## TimeClock – RFID-Based Working Time Tracker

TimeClock is a kiosk-style working time tracker built with **Kivy** and **SQLite (Peewee)**, designed for touch screens and an **RFID reader (pcProx)**.  
Employees clock **IN/OUT** with RFID tags, while HR can export data and generate **Working Time (WT) reports** per employee.  

Tested with Raspberry Pi 3 Model B+, official Raspberry Pi Touchscreen and RFIDeas RDR-80582AKU RFID reader.  

---

## Table of Contents

- [Features Overview](#1-features-overview)
- [Architecture & Data Model](#2-architecture--data-model)
- [RFID Flow](#3-rfid-flow)
- [Clocking Logic](#4-clocking-logic)
- [Working Time (WT) Reports](#5-working-time-wt-reports)
- [UI Overview](#6-ui-overview)
- [Today Summary & Entry Editor](#7-today-summary--entry-editor)
- [Running the Application](#8-running-the-application)
- [Testing & Debugging](#9-testing--debugging)
- [Extending the System](#10-extending-the-system)

## 1. Features Overview

- **RFID-based time tracking**
  - Uses a `PcProx` RFID reader (via `libraries/pcprox.py`)
  - Background thread polls the reader and calls into the UI on each scan
  - Mock provider available for development/testing without hardware

- **Screens / Workflows**
  - `TimeClockScreen`
    - Default kiosk screen
    - Shows current status (e.g. “Clocked IN/OUT – Alice”)
    - RFID scan:
      - Normal employee → toggles IN/OUT and creates a `TimeEntry`
      - Admin tag → switches to the admin screen
      - Unknown tag → shows “Unknown Tag” popup
  - `AdminScreen`
    - Register new users
    - Identify tags
    - Open WT Reports
    - Export all raw time entries to CSV
  - `RegisterScreen`
    - Register employees with:
      - Name
      - RFID tag
      - Admin flag
    - First user must be an admin (enforced)
  - `IdentifyScreen`
    - Scan a tag to see:
      - Employee name
      - Tag ID
      - Role (Admin / Employee)
  - `WTReportScreen`
    - HR-focused “Working Time Report” per employee
    - Optional date range
    - Shows daily sessions and totals
    - Exportable to CSV
  - Today summary overlay
    - After each clock-out an overlay shows “Total worked today” for ~3s
    - Overlay exposes buttons to view the WT report or launch the entry editor
    - Entry editor lets the admin soft-delete duplicate clock-ins/outs

- **Database**
  - SQLite (`timeclock.db`) via Peewee ORM
  - `Employee` table
  - `TimeEntry` table
  - Helper functions for initialization, queries and creation

---

## 2. Architecture & Data Model

### 2.1 Modules

- `src/main.py`
  - Kivy `App` and all Screens
  - RFID event routing and UI logic
- `src/timeclock.kv`
  - Kivy language UI definitions for all screens
- `src/database.py`
  - Peewee models: `Employee`, `TimeEntry`
  - DB helpers: `initialize_db`, `close_db`, `create_employee`, `create_time_entry`, …
- `src/rfid.py`
  - `RFIDProvider` base class (threaded)
  - `PcProxRFIDProvider` for real hardware
  - `MockRFIDProvider` for development
- `src/wt_report.py`
  - `WorkingTimeReport` class + helper to generate/export per-employee WT reports
- `libraries/*.py`
  - Low-level pcProx protocol handling

### 2.2 Database Schema (Peewee)

Employee
--------
id          : AutoField (PK)
name        : CharField, max_length=100, NOT NULL
rfid_tag    : CharField, max_length=50, UNIQUE, indexed, NOT NULL
is_admin    : BooleanField, default False, NOT NULL
created_at  : DateTimeField, default now, NOT NULL
active      : BooleanField, default True (soft delete)

TimeEntry
---------
id          : AutoField (PK)
employee    : ForeignKeyField → Employee (CASCADE)
timestamp   : DateTimeField, indexed, default now, NOT NULL
action      : CharField, max_length=10, values: 'in' | 'out'
active      : BooleanField, default True (soft delete)

Key helpers in `database.py`:

- `initialize_db()` / `close_db()`
- `get_employee_by_tag(tag_id)`
- `get_all_employees(include_inactive=False)`
- `get_admin_count()`
- `create_employee(name, rfid_tag, is_admin)`
- `create_time_entry(employee, action)`
- `get_time_entries_for_export()`

---

## 3. RFID Flow

### 3.1 Provider Selection

from rfid import get_rfid_provider

self.rfid = get_rfid_provider(self.on_rfid_scan, use_mock=False)
self.rfid.start()- `use_mock=False` → try real `PcProxRFIDProvider`, fallback to `MockRFIDProvider` if hardware / `hid` is not available.

### 3.2 End-to-End Flow

RFID Reader → PcProxRFIDProvider._loop()
           → callback(tag_id)
           → TimeClockApp.on_rfid_scan(tag_id)
           → schedule handle_scan(tag_id) on Kivy main thread
           → handle_scan() routes based on current screenPer-screen behavior in `handle_scan(tag_id)`:

- **`register` screen**
  - Existing tag:
    - Admin tag:
      - If at least one admin exists → go to Admin screen
      - Else → show error (can’t reuse tag for first admin)
    - Non-admin tag:
      - Show “Tag already assigned to X”
  - New tag:
    - Sets `RegisterScreen.tag_id` (uppercased)
    - Triggers green LED feedback

- **`identify` screen**
  - Existing tag:
    - Shows employee name, tag ID and role
  - Unknown tag:
    - Shows “Tag ID: … / Status: Unregistered”

- **`timeclock` screen**
  - Unknown tag:
    - “Unknown Tag” popup
  - Admin tag:
    - Switch to Admin screen
  - Normal employee:
    - Calls `perform_clock_action(employee)`

---

## 4. Clocking Logic

### 4.1 Clock Action

`TimeClockApp.perform_clock_action(employee)`:

1. Looks up last `TimeEntry` for this employee:
   - `TimeEntry.get_last_for_employee(employee)`
2. Sets `action`:
   - If last action was `'in'` → new action `'out'`
   - Else → new action `'in'`
3. Calls `create_time_entry(employee, action)` (atomic DB transaction)
4. Updates `TimeClockScreen.status_message`
5. Signals success via RFID LEDs

### 4.2 Employee Registration

`RegisterScreen.save_user()`:

1. Reads:
   - Name from Kivy `TextInput`
   - Tag from `RegisterScreen.tag_id` (set by RFID scan)
   - Admin flag from checkbox
2. Validates:
   - Non-empty name
   - Tag set and at least 4 characters, not just “Waiting for scan…”
3. Calls `create_employee(name, tag, is_admin)`
4. On success:
   - Switches to Admin screen
   - Shows success popup
   - Signals success on RFID

First-time setup:

- If `get_admin_count() == 0` on startup:
  - Force navigation to `RegisterScreen`
  - Force admin checkbox checked+disabled
  - Require first user to be an admin

---

## 5. Working Time (WT) Reports

### 5.1 Purpose

The **WT Report** system gives HR a **per-employee** overview:

- Daily sessions (clock-in / clock-out pairs)
- Hours worked per session and per day
- Total hours for a period
- Average hours per day
- Optional date range (e.g. a month)
- Exportable to CSV

### 5.2 `WorkingTimeReport` class

Defined in `src/wt_report.py`:

- Construction:

from wt_report import WorkingTimeReport

report = WorkingTimeReport(employee, start_date=None, end_date=None)
data = report.generate()- Key responsibilities:
  - Query all `TimeEntry` rows for an employee in a date range
  - Group entries by day
  - Pair `'in'` → `'out'` events into sessions
  - Compute duration per session and per day
  - Summarize totals
  - Provide:
    - `to_csv(filename=None)` → CSV path
    - `to_text()` → formatted multiline string for UI display

**Session pairing rules:**

- For each day:
  - `'in'` followed by `'out'` → one session
  - Multiple pairs per day are supported
  - If:
    - There is an `'out'` without a previous `'in'` → warn and skip
    - There is an `'in'` without a following `'out'` → logged as an open session (not closed in totals)

### 5.3 WTReportScreen (UI)

Defined in:
- Logic: `WTReportScreen` class in `main.py`
- Layout: `WTReportScreen` block in `timeclock.kv`

Capabilities:

- **Select employee**
  - Screen loads all active employees (`get_all_employees`) on enter
  - Creates a vertical list of buttons:
    - Label: `Name (TAGID)`
    - Click → sets selected employee & updates label

- **Date range (optional)**
  - Two text fields:
    - Start date: `YYYY-MM-DD`
    - End date: `YYYY-MM-DD`
  - If left empty → full history

- **Generate report**
  - Calls `generate_wt_report(employee, start_date, end_date)`
  - Validates date format
  - Renders `report.to_text()` into a scrollable label
  - Stores `current_report` for export

- **Export to CSV**
  - Calls `current_report.to_csv()`
  - Saves into `exports/WT_Report_<Employee>_<from>_<to>.csv`
  - Shows popup with saved filename

---

## 6. UI Overview

All screens are defined in `src/timeclock.kv`:

- `WindowManager` – root `ScreenManager`:
  - `TimeClockScreen`
  - `AdminScreen`
  - `RegisterScreen`
  - `IdentifyScreen`
  - `WTReportScreen`

- **Styling:**
  - Global `<Button>` and `<Label>` defaults for consistent font sizes
  - Screen-specific layouts use `BoxLayout`, `GridLayout`, and `ScrollView`
  - Admin and WTReport screens are scrollable to work well on small displays

---

## 7. Today Summary & Entry Editor

- After each **clock-out** we calculate how much time the employee worked today (only active entries).
- A transient overlay displays “Total worked today” for ~3 seconds and exposes:
  - **View entries** → jumps to `WTReportScreen` with today pre-filled so HR can review sessions.
  - **Edit entries** → opens a small editor listing today’s IN/OUT pairs with delete buttons.
- Deleting a session soft-deletes both `TimeEntry` rows (`active=False`), so the history remains tamper-proof while the UI ignores the removed rows (WT reports, totals, exports).
- The overlay & editor use the same `WorkingTimeReport` logic that powers the HR reports, keeping the UX consistent.

## 8. Running the Application

### 8.1 Requirements

See `requirements.txt` for a definitive list. Core dependencies:

- Python 3.x
- `kivy`
- `peewee`
- `hid` (for real RFID hardware; optional if using mock)

Install (example):

```bash
pip install -r requirements.txt
```

### 8.2 Start TimeClock

From the project root:

```bash
python -m src.main
```

On first run:

- Database `timeclock.db` is created if it does not exist.
- No admin present → app forces you to register the first **Admin** user.

---

## 8.3 Export Destinations

- When exporting CSVs (admin export button or WT report), the system prefers any mounted USB stick under `/media`, `/run/media`, or `/mnt`.
- If no USB is available it falls back to the local `exports/` directory inside the project root.
- Override the destination with `TIME_CLOCK_EXPORT_PATH` (e.g. `export TIME_CLOCK_EXPORT_PATH=/mnt/pendrive`) before launching the app.

---

## 9. Testing & Debugging

- **Mock RFID**
  - In `TimeClockApp.build()`, `get_rfid_provider(self.on_rfid_scan, use_mock=False)` can be called with `use_mock=True` during development.
  - You can also use the “Simulate Tag Scan (Debug)” button on the TimeClock screen.

- **Logs**
  - Logging is configured at `DEBUG` level in `main.py`.
  - Logs include:
    - RFID connection / read events
    - Database initialization and errors
    - WT report generation and export info

- **CSV Export**
  - Raw time entries export via Admin → “Export CSV”.
  - WT reports export via WT Report screen → “Export to CSV”.

---

## 10. Extending the System

Some ideas for future extensions:

- Overtime calculation and highlighting
- Absence / vacation integration
- Weekly / monthly aggregated overviews
- Role-based access (separate HR vs Admin vs Employee views)
- REST API for integration with payroll systems

The current architecture (clear separation of **RFID**, **DB**, **UI**, and **reporting**) is intended to make such extensions straightforward.