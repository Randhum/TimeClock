# TimeClock User Guide

> Complete guide for end users and administrators

**Translations:** [Deutsch (German)](USER_GUIDE_DE.md) | [Italiano (Italian)](USER_GUIDE_IT.md)

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [For Employees](#for-employees)
3. [For Administrators](#for-administrators)
4. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Launch

When you first start TimeClock, you'll be prompted to register an **Administrator**. This is mandatory and cannot be skipped.

**Steps:**
1. Enter the administrator's full name
2. Scan an RFID badge (or enter tag ID manually)
3. The admin checkbox will be automatically checked and locked
4. Click **Save** to complete registration

Once registered, the administrator badge can be used to access all management functions.

---

## For Employees

### Clocking In/Out

**How to clock in or out:**
1. Stand in front of the TimeClock terminal
2. Hold your RFID badge near the reader
3. Wait for the green LED flash (confirms successful scan)
4. A friendly greeting message will appear (disappears after 8 seconds)
5. Your status will update on screen

**What happens:**
- The system automatically determines if you're clocking **IN** or **OUT** based on your last action
- If your last action was OUT (or you haven't clocked in today), you'll clock **IN**
- If your last action was IN, you'll clock **OUT**

### Viewing Today's Summary

After each clock action, you'll see:
- A friendly greeting message
- A status message showing your clock action (e.g., "Clocked IN - Your Name")
- Two action buttons:
  - **View Today's Sessions** - See detailed breakdown of today's sessions
  - **Edit Today's Sessions** - Remove duplicate scans or correct errors

**Note:** The action buttons remain visible at all times. If you click them after the initial grace period (2 minutes), you'll need to scan your badge again for identification.

### Editing Your Time Entries

You can edit your time entries from the past 7 days:

1. **Within 2 minutes of clocking:** Click **Edit Today's Sessions** (no badge scan needed)
2. **After 2 minutes:** Click **Edit Today's Sessions** and scan your badge when prompted
3. Select the date you want to edit (past 7 days only)
4. View all entries for that day
5. Select entries to delete (removes duplicate scans)
6. Or add manual entries if you forgot to clock in/out

**Important:** Deleted entries are not permanently removed—they're marked as inactive for audit purposes.

### Manual Entry

If you forgot to clock in or out:

1. Access the entry editor (see above)
2. Click **Add Entry**
3. Select the date (past 7 days only)
4. Set the time
5. Save

**Note:** The system automatically determines whether the entry should be IN or OUT based on your existing entries for that day.

### Removing Duplicate Scans

**Problem:** You accidentally scanned your badge twice, creating duplicate entries.

**Solution:**
1. Click **Edit Today's Sessions** (within 2 minutes of clocking, no badge scan needed)
2. Or scan badge → **Edit Today's Sessions** (if more than 2 minutes have passed)
3. Select the date
4. Check the duplicate entries
5. Click **Delete Selected**
6. Confirm deletion

### Correcting Forgotten Clock-Out

**Problem:** You forgot to clock out yesterday.

**Solution:**
1. Scan badge → **Edit Today's Sessions**
2. Select yesterday's date
3. Click **Add Entry**
4. Set the time (e.g., end of workday)
5. Save

The system will automatically pair this with the existing clock-in entry.

### Tips for Employees

- **Scan once:** The system debounces rapid scans, but it's best to scan once and wait for confirmation
- **Check your status:** After scanning, verify the greeting message shows the correct action (IN/OUT)
- **Use the action buttons:** If you notice an error after clocking, use the action buttons to quickly edit your sessions
- **Regular checks:** Periodically review your time entries to catch any issues early

---

## For Administrators

### Accessing Admin Panel

Scan your administrator badge at any time to access the admin panel. The screen will automatically switch to admin mode.

### Registering New Employees

1. Navigate to **Admin → Register User**
2. Enter the employee's full name
3. Scan their RFID badge (or enter tag ID manually)
4. Leave the admin checkbox **unchecked** (unless creating another admin)
5. Click **Save**

**Note:** Each badge can only be assigned to one employee. If you try to register a badge that's already in use, you'll see an error message.

### Identifying Badges

To check which employee a badge belongs to:

1. Navigate to **Admin → Identify Tag**
2. Scan the badge
3. View the information displayed:
   - Employee name
   - Tag ID
   - Role (Administrator or Employee)
   - Registration status

### Generating Working Time Reports

1. Navigate to **Admin → WT Reports**
2. Select an employee from the dropdown
3. (Optional) Set a date range:
   - Click **Select Dates**
   - Choose start and end dates
   - Click **Confirm**
4. Click **Generate Report**
5. Review the report showing:
   - Daily breakdown of sessions
   - Clock in/out times
   - Duration per session
   - Daily totals
   - Period summary (total hours, average per day)
6. Export options:
   - **Export to Excel** - Structured spreadsheet with hours per day per month
   - **Export to CSV** - Semicolon-delimited format for payroll systems
   - **Export to PDF** - Formatted report for printing

**Report Features:**
- Automatically pairs clock-in and clock-out events
- Calculates total hours worked from actual stamped entries
- Shows daily averages
- Flags open sessions (if employee forgot to clock out)
- Export formats show hours per day organized by month

**Export Format:**
The exported files show working hours per day in a simple, clear format:
- Employee name and date range at the top
- Each month listed separately
- Day numbers (1-31) across the top
- Hours worked per day in H:MM format below
- Monthly totals in the rightmost column

### Exporting Data

**Export Raw Time Entries (CSV):**
1. Navigate to **Admin → Export CSV**
2. Click **Export Time Entries**
3. File will be saved to USB drive (if connected) or `exports/` directory
4. A confirmation popup shows the file path
5. Contains raw clock in/out entries with timestamps

**Export Working Hours Reports:**
1. Navigate to **Admin → WT Reports**
2. Select employee and date range
3. Generate report
4. Choose export format:
   - **Excel** - For spreadsheet applications (`.xlsx`)
   - **CSV** - For import into payroll systems (`.csv`, semicolon-delimited)
   - **PDF** - For printing and documentation (`.pdf`)
5. Files are saved with format: `Arbeitszeit_[EmployeeName]_[StartDate]_[EndDate].[ext]`

**Export Database Backup:**
1. Navigate to **Admin → Export Database**
2. Click **Export Database**
3. Full SQLite database backup will be created
4. Useful for backups or migrating to another system

**Export Locations:**
- USB drives are automatically detected (`/media`, `/run/media`, `/mnt`)
- If no USB is found, files save to `exports/` directory
- You can override with environment variable: `export TIME_CLOCK_EXPORT_PATH=/custom/path`

### Tips for Administrators

- **Regular backups:** Export the database regularly for backup purposes
- **Monitor reports:** Generate weekly reports to spot patterns or issues
- **Badge management:** Keep track of which badges are assigned to which employees
- **Test hardware:** Periodically test RFID reader functionality using Identify Tag feature

---

## Troubleshooting

### Badge Not Recognized

**Symptoms:** Red LED flash, "Unknown Tag" message

**Solutions:**
- Ensure badge is held close to reader (within 2-3 cm)
- Try scanning again (wait 1-2 seconds between scans)
- Check if badge is registered: Admin → Identify Tag
- Contact administrator to register badge

### Can't Access Admin Functions

**Symptoms:** Admin badge doesn't switch to admin screen

**Solutions:**
- Verify badge is registered as administrator
- Check badge assignment: Admin → Identify Tag
- Ensure you're scanning the correct badge
- Try restarting the application

### Export Not Working

**Symptoms:** Export button doesn't create file, or file not found

**Solutions:**
- Check USB drive is properly mounted
- Verify USB has write permissions
- Check `exports/` directory exists and is writable
- Review application logs for error messages
- Try setting custom export path: `export TIME_CLOCK_EXPORT_PATH=/tmp`

### Screen Goes Blank (Screensaver)

**Symptoms:** Screen shows Matrix-style animation after inactivity

**Solutions:**
- This is normal behavior (activates after 60 seconds idle)
- Touch the screen or scan a badge to wake it up
- Screen will return to the previous screen

### Buttons Not Responding

**Symptoms:** Button appears pressed but doesn't trigger action

**Solutions:**
- Ensure you complete the tap (press and release)
- Wait a moment between taps (rapid double-taps are debounced)
- If using touch screen, ensure finger fully lifts before tapping again

---

*Last updated: Jan 2026*
