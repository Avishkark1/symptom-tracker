import json
import os
import csv
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date

try:
    import winsound
except Exception:
    winsound = None

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:
    pystray = None
    Image = None
    ImageDraw = None

APP_TITLE = "Symptom Tracker"
DATA_FILE = "data.json"
REMINDERS_FILE = "reminders.json"
DATE_FMT = "%Y-%m-%d"


def today_str():
    return date.today().strftime(DATE_FMT)


def parse_date(value):
    try:
        return datetime.strptime(value.strip(), DATE_FMT).date()
    except Exception:
        return None


def parse_time(value):
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except Exception:
        return None


class SymptomTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x620")
        self.minsize(880, 560)

        self.data = []
        self.filtered = []
        self.reminders = []
        self.reminder_last_fired = {}
        self.tray_icon = None
        self.tray_thread = None
        self.tray_hint_shown = False

        self._build_ui()
        self._load_data()
        self._load_reminders()
        self._refresh_table()
        self._refresh_reminders()
        self._schedule_reminder_checks()
        self._setup_tray()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            header,
            text="Log symptoms, track patterns, and export your history.",
            font=("Segoe UI", 10),
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        main = ttk.Frame(self, padding=12)
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(1, weight=1)

        form = ttk.LabelFrame(main, text="New Entry", padding=12)
        form.grid(row=0, column=0, sticky="new", padx=(0, 10))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Date (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.date_var = tk.StringVar(value=today_str())
        self.date_entry = ttk.Entry(form, textvariable=self.date_var)
        self.date_entry.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Symptom").grid(row=1, column=0, sticky="w")
        self.symptom_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.symptom_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Severity (1-10)").grid(row=2, column=0, sticky="w")
        self.severity_var = tk.StringVar(value="5")
        ttk.Combobox(
            form,
            textvariable=self.severity_var,
            values=[str(i) for i in range(1, 11)],
            state="readonly",
            width=5,
        ).grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(form, text="Duration").grid(row=3, column=0, sticky="w")
        self.duration_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.duration_var).grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Possible Triggers").grid(row=4, column=0, sticky="w")
        self.triggers_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.triggers_var).grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Notes").grid(row=5, column=0, sticky="nw")
        self.notes_text = tk.Text(form, height=6, wrap="word")
        self.notes_text.grid(row=5, column=1, sticky="ew", pady=4)

        btns = ttk.Frame(form)
        btns.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        ttk.Button(btns, text="Add Entry", command=self._add_entry).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=self._clear_form).grid(row=0, column=1, sticky="ew")

        filter_frame = ttk.LabelFrame(main, text="Filter", padding=12)
        filter_frame.grid(row=1, column=0, sticky="new", padx=(0, 10), pady=(10, 0))
        filter_frame.columnconfigure(1, weight=1)

        ttk.Label(filter_frame, text="Search").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew", pady=4)
        search_entry.bind("<KeyRelease>", lambda _event: self._apply_filter())

        ttk.Label(filter_frame, text="From").grid(row=1, column=0, sticky="w")
        self.from_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.from_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(filter_frame, text="To").grid(row=2, column=0, sticky="w")
        self.to_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.to_var).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Button(filter_frame, text="Apply", command=self._apply_filter).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(filter_frame, text="Reset", command=self._reset_filter).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        reminders_frame = ttk.LabelFrame(main, text="Reminders", padding=12)
        reminders_frame.grid(row=2, column=0, sticky="new", padx=(0, 10), pady=(10, 0))
        reminders_frame.columnconfigure(1, weight=1)

        ttk.Label(reminders_frame, text="Time (HH:MM)").grid(row=0, column=0, sticky="w")
        self.reminder_time_var = tk.StringVar()
        ttk.Entry(reminders_frame, textvariable=self.reminder_time_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(reminders_frame, text="Message").grid(row=1, column=0, sticky="w")
        self.reminder_message_var = tk.StringVar()
        ttk.Entry(reminders_frame, textvariable=self.reminder_message_var).grid(row=1, column=1, sticky="ew", pady=4)

        reminder_btns = ttk.Frame(reminders_frame)
        reminder_btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        reminder_btns.columnconfigure(0, weight=1)
        reminder_btns.columnconfigure(1, weight=1)

        ttk.Button(reminder_btns, text="Add Reminder", command=self._add_reminder).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(reminder_btns, text="Remove Selected", command=self._delete_reminder).grid(row=0, column=1, sticky="ew")

        self.reminder_list = tk.Listbox(reminders_frame, height=5)
        self.reminder_list.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        table_frame = ttk.Frame(main)
        table_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("date", "symptom", "severity", "duration", "triggers")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        self.table.heading("date", text="Date")
        self.table.heading("symptom", text="Symptom")
        self.table.heading("severity", text="Severity")
        self.table.heading("duration", text="Duration")
        self.table.heading("triggers", text="Triggers")

        self.table.column("date", width=110, anchor="center")
        self.table.column("symptom", width=160)
        self.table.column("severity", width=80, anchor="center")
        self.table.column("duration", width=120)
        self.table.column("triggers", width=220)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        actions = ttk.Frame(table_frame)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)

        ttk.Button(actions, text="Delete Selected", command=self._delete_selected).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="Export CSV", command=self._export_csv).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(actions, text="Show All", command=self._reset_filter).grid(row=0, column=2, sticky="ew")

        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=6, relief="sunken")
        status.grid(row=2, column=0, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _data_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_FILE)

    def _reminder_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), REMINDERS_FILE)

    def _load_data(self):
        path = self._data_path()
        if not os.path.exists(path):
            self.data = []
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                self.data = json.load(handle)
        except Exception as exc:
            messagebox.showwarning("Load Error", f"Could not read data file. Starting fresh.\n\n{exc}")
            self.data = []

    def _save_data(self):
        path = self._data_path()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2)

    def _load_reminders(self):
        path = self._reminder_path()
        if not os.path.exists(path):
            self.reminders = []
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                self.reminders = json.load(handle)
        except Exception as exc:
            messagebox.showwarning("Load Error", f"Could not read reminders file. Starting fresh.\n\n{exc}")
            self.reminders = []

    def _save_reminders(self):
        path = self._reminder_path()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.reminders, handle, indent=2)

    def _add_entry(self):
        date_value = self.date_var.get().strip()
        symptom = self.symptom_var.get().strip()
        severity = self.severity_var.get().strip()
        duration = self.duration_var.get().strip()
        triggers = self.triggers_var.get().strip()
        notes = self.notes_text.get("1.0", "end").strip()

        parsed_date = parse_date(date_value)
        if not parsed_date:
            messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format.")
            return
        if not symptom:
            messagebox.showerror("Missing Symptom", "Please enter a symptom name.")
            return

        entry = {
            "id": datetime.utcnow().isoformat(timespec="seconds"),
            "date": parsed_date.strftime(DATE_FMT),
            "symptom": symptom,
            "severity": severity,
            "duration": duration,
            "triggers": triggers,
            "notes": notes,
        }
        self.data.append(entry)
        self._save_data()
        self._clear_form()
        self._apply_filter()
        self.status_var.set(f"Added entry for {entry['date']}")

    def _clear_form(self):
        self.date_var.set(today_str())
        self.symptom_var.set("")
        self.severity_var.set("5")
        self.duration_var.set("")
        self.triggers_var.set("")
        self.notes_text.delete("1.0", "end")

    def _apply_filter(self):
        query = self.search_var.get().strip().lower()
        from_date = parse_date(self.from_var.get()) if self.from_var.get().strip() else None
        to_date = parse_date(self.to_var.get()) if self.to_var.get().strip() else None

        if self.from_var.get().strip() and not from_date:
            self.status_var.set("Invalid 'From' date. Use YYYY-MM-DD.")
            return
        if self.to_var.get().strip() and not to_date:
            self.status_var.set("Invalid 'To' date. Use YYYY-MM-DD.")
            return

        results = []
        for entry in self.data:
            entry_date = parse_date(entry.get("date", ""))
            if from_date and entry_date and entry_date < from_date:
                continue
            if to_date and entry_date and entry_date > to_date:
                continue

            if query:
                haystack = " ".join(
                    [
                        entry.get("symptom", ""),
                        entry.get("triggers", ""),
                        entry.get("notes", ""),
                    ]
                ).lower()
                if query not in haystack:
                    continue

            results.append(entry)

        self.filtered = results
        self._refresh_table()
        self.status_var.set(f"Showing {len(self.filtered)} of {len(self.data)} entries")

    def _reset_filter(self):
        self.search_var.set("")
        self.from_var.set("")
        self.to_var.set("")
        self.filtered = list(self.data)
        self._refresh_table()
        self.status_var.set(f"Showing {len(self.filtered)} of {len(self.data)} entries")

    def _refresh_table(self):
        self.table.delete(*self.table.get_children())
        rows = self.filtered if self.filtered else list(self.data)
        for entry in rows:
            self.table.insert(
                "",
                "end",
                iid=entry.get("id"),
                values=(
                    entry.get("date", ""),
                    entry.get("symptom", ""),
                    entry.get("severity", ""),
                    entry.get("duration", ""),
                    entry.get("triggers", ""),
                ),
            )

    def _refresh_reminders(self):
        self.reminder_list.delete(0, "end")
        for reminder in self.reminders:
            label = f"{reminder.get('time', '')} - {reminder.get('message', '')}"
            self.reminder_list.insert("end", label)

    def _add_reminder(self):
        time_value = self.reminder_time_var.get().strip()
        message = self.reminder_message_var.get().strip()

        parsed_time = parse_time(time_value)
        if not parsed_time:
            messagebox.showerror("Invalid Time", "Please enter a valid time in HH:MM (24h) format.")
            return
        if not message:
            messagebox.showerror("Missing Message", "Please enter a reminder message.")
            return

        reminder = {
            "id": datetime.utcnow().isoformat(timespec="seconds"),
            "time": parsed_time.strftime("%H:%M"),
            "message": message,
        }
        self.reminders.append(reminder)
        self._save_reminders()
        self._refresh_reminders()
        self.reminder_time_var.set("")
        self.reminder_message_var.set("")
        self.status_var.set(f"Added reminder at {reminder['time']}")

    def _delete_reminder(self):
        selection = self.reminder_list.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Select a reminder to remove.")
            return
        index = selection[0]
        removed = self.reminders.pop(index)
        self._save_reminders()
        self._refresh_reminders()
        self.status_var.set(f"Removed reminder at {removed.get('time', '')}")

    def _schedule_reminder_checks(self):
        self._check_reminders()
        self.after(30000, self._schedule_reminder_checks)

    def _check_reminders(self):
        if not self.reminders:
            return
        now = datetime.now()
        now_date = now.strftime(DATE_FMT)
        now_time = now.strftime("%H:%M")

        for reminder in self.reminders:
            reminder_id = reminder.get("id")
            if reminder.get("time") != now_time:
                continue
            if self.reminder_last_fired.get(reminder_id) == now_date:
                continue
            self.reminder_last_fired[reminder_id] = now_date
            if winsound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except Exception:
                    pass
            messagebox.showinfo("Reminder", reminder.get("message", "Time for your reminder."))

    def _setup_tray(self):
        if not pystray or not Image or not ImageDraw:
            self.status_var.set("Tray disabled (missing pystray/Pillow).")
            return

        def create_image():
            image = Image.new("RGB", (64, 64), color=(20, 95, 140))
            draw = ImageDraw.Draw(image)
            draw.rectangle((8, 8, 56, 56), outline=(255, 255, 255), width=4)
            draw.line((18, 34, 30, 46), fill=(255, 255, 255), width=5)
            draw.line((30, 46, 48, 22), fill=(255, 255, 255), width=5)
            return image

        def on_open(_icon, _item):
            self.after(0, self._show_main)

        def on_quit(_icon, _item):
            self.after(0, self._quit_app)

        icon = pystray.Icon(
            "symptom-tracker",
            create_image(),
            APP_TITLE,
            menu=pystray.Menu(
                pystray.MenuItem("Open", on_open),
                pystray.MenuItem("Quit", on_quit),
            ),
        )
        self.tray_icon = icon

        def run_tray():
            try:
                icon.run()
            except Exception:
                pass

        self.tray_thread = threading.Thread(target=run_tray, daemon=True)
        self.tray_thread.start()

    def _show_main(self):
        self.deiconify()
        self.lift()
        self.status_var.set("Ready")

    def _on_close(self):
        if self.tray_icon:
            self.withdraw()
            if not self.tray_hint_shown:
                self.tray_hint_shown = True
                messagebox.showinfo("Still Running", "Symptom Tracker is still running in the system tray.")
            return
        self._quit_app()

    def _quit_app(self):
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()
        sys.exit(0)

    def _delete_selected(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Select one or more entries to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", f"Delete {len(selected)} selected entr{'y' if len(selected)==1 else 'ies'}?"):
            return

        ids = set(selected)
        self.data = [entry for entry in self.data if entry.get("id") not in ids]
        self._save_data()
        self._apply_filter()
        self.status_var.set("Deleted selected entries")

    def _export_csv(self):
        if not self.data:
            messagebox.showinfo("No Data", "Add at least one entry before exporting.")
            return

        default_name = f"symptom-tracker-{today_str()}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=default_name,
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["date", "symptom", "severity", "duration", "triggers", "notes"],
                )
                writer.writeheader()
                for entry in self.data:
                    writer.writerow(entry)
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not export CSV.\n\n{exc}")
            return

        self.status_var.set(f"Exported CSV to {path}")


if __name__ == "__main__":
    app = SymptomTrackerApp()
    app.mainloop()
