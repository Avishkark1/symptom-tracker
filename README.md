# Symptom Tracker (Desktop)

A simple, offline desktop symptom tracker built with Python and Tkinter. Your data is stored locally next to the app.

## Run

```powershell
python .\main.py
```

## Features

- Log symptoms with date, severity, duration, triggers, and notes
- Filter by search text and date range
- Delete selected entries
- Export to CSV
- Daily pop-up reminders (app must be open)
- Reminder sound + system tray icon

## Data

- Local file: `data.json`
- Format: JSON list of entries
- Local file: `reminders.json`
- Format: JSON list of reminders

## System Tray Setup

Install the optional dependencies:

```powershell
pip install pystray pillow
```

If these are missing, the app still runs but without the tray icon.
