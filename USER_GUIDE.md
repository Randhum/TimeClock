# TimeClock User Guide

> Complete guide for end users and administrators

**Translations:** [Deutsch (German)](USER_GUIDE_DE.md) | [Italiano (Italian)](USER_GUIDE_IT.md)

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [For Employees](#for-employees)
3. [For Administrators](#for-administrators)
4. [Common Tasks](#common-tasks)
5. [Troubleshooting](#troubleshooting)

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
4. A friendly greeting message will appear
5. Your status will update on screen

**What happens:**
- The system automatically determines if you're clocking **IN** or **OUT** based on your last action
- If your last action was OUT (or you haven't clocked in today), you'll clock **IN**
- If your last action was IN, you'll clock **OUT**

### Viewing Today's Summary

After each clock action, you'll see:
- A brief summary showing total hours worked today
- Two action buttons (visible for 5 seconds):
  - **View Today's Report** - See detailed breakdown of today's sessions
  - **Edit Today's Sessions** - Remove duplicate scans or correct errors

**After 5 seconds:**
- The action buttons disappear
- To access these features later, you'll need to scan your badge again for identification

### Editing Your Time Entries

You can edit your time entries from the past 7 days:

1. **Within 5 seconds of clocking:** Click **Edit Today's Sessions**
2. **After 5 seconds:** Scan your badge when prompted
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
4. Choose **Clock In** or **Clock Out**
5. Set the time
6. Save

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
6. (Optional) Click **Export to CSV** to save for payroll

**Report Features:**
- Automatically pairs clock-in and clock-out events
- Calculates total hours worked
- Shows daily averages
- Flags open sessions (if employee forgot to clock out)

### Exporting Data

**Export Raw Time Entries:**
1. Navigate to **Admin → Export CSV**
2. Click **Export Time Entries**
3. File will be saved to USB drive (if connected) or `exports/` directory
4. A confirmation popup shows the file path

**Export Database Backup:**
1. Navigate to **Admin → Export Database**
2. Click **Export Database**
3. Full SQLite database backup will be created
4. Useful for backups or migrating to another system

**Export Locations:**
- USB drives are automatically detected (`/media`, `/run/media`, `/mnt`)
- If no USB is found, files save to `exports/` directory
- You can override with environment variable: `export TIME_CLOCK_EXPORT_PATH=/custom/path`

---

## Common Tasks

### Removing Duplicate Scans

**Problem:** Employee accidentally scanned badge twice, creating duplicate entries.

**Solution:**
1. Within 5 seconds of clocking: Click **Edit Today's Sessions**
2. Or scan badge → **Edit Today's Sessions**
3. Select the date
4. Check the duplicate entries
5. Click **Delete Selected**
6. Confirm deletion

The duplicate entries will be removed from reports but preserved in the database for audit purposes.

### Correcting Forgotten Clock-Out

**Problem:** Employee forgot to clock out yesterday.

**Solution:**
1. Scan badge → **Edit Today's Sessions**
2. Select yesterday's date
3. Click **Add Entry**
4. Choose **Clock Out**
5. Set the time (e.g., end of workday)
6. Save

The system will automatically pair this with the existing clock-in entry.

### Viewing Employee Hours

**For employees:**
- View today's summary immediately after clocking
- Or scan badge → **View Today's Report**

**For administrators:**
- Navigate to **Admin → WT Reports**
- Select employee and date range
- Generate report

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

### Double Character Input

**Symptoms:** When typing, each character appears twice

**Solutions:**
- This is automatically handled by the application
- If it persists, try tapping more slowly
- The system filters duplicate keystrokes automatically

---

## Tips & Best Practices

### For Employees

- **Scan once:** The system debounces rapid scans, but it's best to scan once and wait for confirmation
- **Check your status:** After scanning, verify the greeting message shows the correct action (IN/OUT)
- **Use the 5-second window:** If you notice an error immediately after clocking, use the quick action buttons
- **Regular checks:** Periodically review your time entries to catch any issues early

### For Administrators

- **Regular backups:** Export the database regularly for backup purposes
- **Monitor reports:** Generate weekly reports to spot patterns or issues
- **Badge management:** Keep track of which badges are assigned to which employees
- **Test hardware:** Periodically test RFID reader functionality using Identify Tag feature

---

## Support

For technical issues or questions:
- Check the troubleshooting section above
- Review application logs
- Contact your system administrator

---

*Last updated: Dec 2025*

