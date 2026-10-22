"""
SomaiyaSat & SomaiyaPod Mission Dashboard
=========================================

A beginner-friendly, desktop-only demonstration application for a college
Python lab project.

IMPORTANT (honesty requirement - please do not strip this):
-----------------------------------------------------------
This is a *simulation/demonstration* desktop application.  It does NOT
communicate with any real satellite, does NOT transmit or decode radio
signals, and does NOT run a trained AI model.  All telemetry is generated
locally as *simulated sample data* and the "routing" feature is a tiny,
transparent, rule-based demo.  If you present this as an AI/radio system in
a viva, you must be clear that the AI is only a rule-based demo and the
radio payloads are simulated.

Topics covered by the project title:
  * PocketQube / Colony-Class miniature satellites (SomaiyaSat & SomaiyaPod)
  * Autonomous AI-based inter-satellite data routing (simulated here)
  * Advanced multi-mode amateur radio payloads: M17, Codec2, SSTV,
    TT&C / Housekeeping

Tech stack (standard library only):
  * Python 3 + Tkinter/ttk      -> desktop GUI
  * SQLite                      -> persistent storage (no server needed)
  * csv, datetime, os, random   -> CSV export and demo data generation

How to run
----------
  1. Install Python from https://www.python.org/downloads/ and tick
     "Add Python to PATH" during installation.
  2. Open a terminal in this folder.
  3. Run:  python main.py

The SQLite database (missions.db) is created automatically on the first run.

Files
-----
  main.py            - the complete application
  missions.db        - created automatically on first run
  README.md          - this documentation
"""

from __future__ import annotations

import csv
import random
import sqlite3
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from tkinter import filedialog
except ImportError:  # pragma: no cover
    filedialog = None

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
DB_NAME = "missions.db"

# Full path of the database file, always next to this script.
DB_PATH = str(Path(__file__).resolve().parent / DB_NAME)

# Columns in the missions table.
COLS = [
    "id",
    "satellite_name",
    "timestamp",
    "mode",
    "battery_voltage",
    "signal_strength",
    "temperature",
    "packet_status",
    "notes",
]

# Full allowed communication modes (matches the lab spec).
MODES = ["M17", "Codec2", "SSTV", "TT&C / Housekeeping"]

# Default demo records inserted when the user clicks the demo button.
# Every record is clearly labelled with a [DEMO] tag so it can never be
# mistaken for real flight data.
DEFAULT_DEMO_RECORDS = [
    ("SomaiyaSat-1 [DEMO]", "2026-10-22 08:15:00", "M17", 3.2, -95.0, 21.5, 1, "DEMO: Msg 0x1A"),
    ("SomaiyaPod-2 [DEMO]", "2026-10-22 08:16:00", "Codec2", 3.4, -91.0, 22.0, 1, "DEMO: Codec speech"),
    ("SomaiyaSat-1 [DEMO]", "2026-10-22 08:17:00", "SSTV", 3.1, -101.0, 19.8, 1, "DEMO: SSTV image"),
    ("SomaiyaPod-2 [DEMO]", "2026-10-22 08:18:00", "TT&C / Housekeeping", 3.3, -88.0, 23.1, 1, "DEMO: Status frame"),
]

# Battery voltage limits (in volts) accepted for a physically plausible
# amateur/PocketQube payload bus.  Used for validation only (simulation).
MIN_VOLTAGE = 2.5
MAX_VOLTAGE = 4.5
MIN_SIGNAL = -120.0
MAX_SIGNAL = -30.0
MIN_TEMP = -40.0
MAX_TEMP = 85.0

# Sentinel used to tell "user typed a bad number" apart from "field was empty".
_INVALID = object()


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
class Database:
    """Encapsulates all SQLite access so the GUI does not need to know SQL."""

    def __init__(self, db_path: str | None = None):
        # Resolve the path at call time (not at import time) so the app
        # always stores its database next to this file.
        self.db_path = db_path or DB_PATH
        self._init_db()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def _init_db(self) -> None:
        """Create the database and table on the very first run only."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    satellite_name TEXT NOT NULL,
                    timestamp     TEXT NOT NULL,
                    mode          TEXT NOT NULL,
                    battery_voltage REAL,
                    signal_strength REAL,
                    temperature   REAL,
                    packet_status INTEGER NOT NULL,
                    notes         TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def modes(self) -> list[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT DISTINCT mode FROM missions ORDER BY mode"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def recent(self, limit: int = 5) -> list[tuple]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM missions ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return rows
        finally:
            conn.close()

    def all_records(self) -> list[tuple]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM missions ORDER BY timestamp DESC"
            ).fetchall()
            return rows
        finally:
            conn.close()

    def search(self, satellite: str, mode: str) -> list[tuple]:
        conn = sqlite3.connect(self.db_path)
        try:
            sql = "SELECT * FROM missions WHERE 1=1"
            params: list = []
            if satellite:
                sql += " AND satellite_name LIKE ?"
                params.append(f"%{satellite}%")
            if mode:
                sql += " AND mode = ?"
                params.append(mode)
            sql += " ORDER BY timestamp DESC"
            rows = conn.execute(sql, params).fetchall()
            return rows
        finally:
            conn.close()

    def insert(self, record: tuple) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO missions
                    (satellite_name, timestamp, mode, battery_voltage,
                     signal_strength, temperature, packet_status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                record,
            )
            conn.commit()
        finally:
            conn.close()

    def update(self, record: tuple) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                UPDATE missions SET
                    satellite_name = ?, timestamp = ?, mode = ?,
                    battery_voltage = ?, signal_strength = ?,
                    temperature = ?, packet_status = ?, notes = ?
                WHERE id = ?
                """,
                (*record[:8], record[8]),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, record_id: int) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM missions WHERE id = ?", (record_id,))
            conn.commit()
        finally:
            conn.close()

    def count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM missions").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

    def names(self) -> list[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT DISTINCT satellite_name FROM missions ORDER BY satellite_name"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def export_to_csv(self, path: str) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerow(COLS)
                writer.writerows(conn.execute("SELECT * FROM missions ORDER BY timestamp DESC"))
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Simulated telemetry + rule-based routing demo
# ---------------------------------------------------------------------------
def generate_demo_records(count: int = 6) -> list[tuple]:
    """Generate *simulated* telemetry rows for the demo button.

    All values are purely synthetic.  Callers must treat them as
    demonstration data only.
    """
    satellites = ["SomaiyaSat-1", "SomaiyaPod-2", "SomaiyaSat-3", "SomaiyaPod-4"]
    now = datetime.now()
    records = []
    for i in range(count):
        sat = random.choice(satellites)
        mode = random.choice(MODES)
        voltage = round(random.uniform(MIN_VOLTAGE + 0.2, MAX_VOLTAGE - 0.2), 2)
        signal = round(random.uniform(MIN_SIGNAL + 5, MAX_SIGNAL - 5), 1)
        temp = round(random.uniform(MIN_TEMP + 2, MAX_TEMP - 2), 1)
        packet_status = random.choice([0, 1, 2])  # 0=ok, 1=warn, 2=critical
        notes = random.choice(
            [
                "Periodic housekeeping downlink",
                "Voice burst (M17 voice channel)",
                "Codec2 audio packet",
                "SSTV image received",
                "Status/response frame",
            ]
        )
        records.append(
            (
                f"{sat} [DEMO]",
                (now - timedelta(minutes=i * 3)).strftime("%Y-%m-%d %H:%M:%S"),
                mode,
                voltage,
                signal,
                temp,
                packet_status,
                f"DEMO: {notes}",
            )
        )
    return records


def compute_route(records: list[tuple]) -> list[int]:
    """Rule-based routing demo: pick the best record per pass.

    This is intentionally simple and transparent for the lab demo:
    records are ranked by (signal strength ascending, packet status
    ascending, battery voltage descending) and the top few
    candidate ids are returned.  No machine learning, no real radio
    communications, no actual satellite network is involved.

    Returns a list of record ids (not the record objects) that the
    demo table should highlight as the "recommended route".
    """
    if not records:
        return []
    ranked = sorted(
        records,
        key=lambda r: (
            -(r[5] if r[5] is not None else -999.0),
                                # signal_strength: dBm is negative, so negate it
                                # so that a STRONGER signal sorts first
            r[7],               # packet_status (0 = ok is best)
            -(r[4] or 0.0),     # battery voltage descending (None -> 0)
        ),
    )
    return [r[0] for r in ranked[:3]]


# ---------------------------------------------------------------------------
# The graphical application
# ---------------------------------------------------------------------------
class App(tk.Tk):
    """Main window.  One class, one clear job: show and edit mission records."""

    def __init__(self) -> None:
        super().__init__()
        self.title("SomaiyaSat & SomaiyaPod - Mission Dashboard")
        self.geometry("1180x720")
        self.minsize(980, 600)

        self.db = Database()
        self.current_view = "dashboard"
        self.selected_id = None
        self.route_ids: list[int] = []

        self._configure_styles()
        self._build_layout()
        self.refresh_all()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _configure_styles(self) -> None:
        """Give the app a clean, modern look using ttk styles only."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # Not every platform ships "clam"; the default is fine.

        bg = "#0f172a"
        card = "#1e293b"
        text = "#e2e8f0"
        muted = "#94a3b8"
        accent = "#38bdf8"

        self.configure(bg=bg)
        style.configure("App.TFrame", background=bg)
        style.configure("Sidebar.TFrame", background="#111c33")
        style.configure("Card.TFrame", background=card)
        style.configure(
            "Nav.TButton",
            background="#111c33",
            foreground=text,
            font=("Segoe UI", 11),
            padding=(14, 10),
            anchor="w",
        )
        style.map(
            "Nav.TButton",
            background=[("active", "#1e293b"), ("pressed", accent)],
        )
        style.configure(
            "Title.TLabel",
            background=bg,
            foreground=text,
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background=bg,
            foreground=muted,
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=card,
            foreground=muted,
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardValue.TLabel",
            background=card,
            foreground=accent,
            font=("Segoe UI", 22, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background=bg,
            foreground=text,
            font=("Segoe UI", 13, "bold"),
        )
        style.configure(
            "Field.TLabel",
            background=bg,
            foreground=text,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Data.Treeview",
            background=card,
            fieldbackground=card,
            foreground=text,
            rowheight=28,
        )
        style.map(
            "Data.Treeview",
            background=[("selected", accent)],
            foreground=[("selected", "#0f172a")],
        )
        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="#0f172a",
            font=("Segoe UI", 10, "bold"),
            padding=(10, 7),
        )
        style.map("Accent.TButton", background=[("active", "#7dd3fc")])
        style.configure("TEntry", padding=4)
        style.configure("TCombobox", padding=4)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        """Build the sidebar navigation and the main content area."""
        self.sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg="#111c33")
        brand.pack(fill="x", padx=16, pady=(18, 10))
        tk.Label(
            brand,
            text="SomaiyaSat\n& SomaiyaPod",
            bg="#111c33",
            fg="#38bdf8",
            font=("Segoe UI", 14, "bold"),
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="Mission Dashboard",
            bg="#111c33",
            fg="#94a3b8",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        nav_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        nav_frame.pack(fill="x", padx=10)

        self.nav_buttons = {}
        for key, label in (
            ("dashboard", "  Dashboard"),
            ("records", "  Mission Records"),
            ("add", "  Add Record"),
            ("about", "  About / Help"),
        ):
            btn = ttk.Button(
                nav_frame,
                text=label,
                style="Nav.TButton",
                command=lambda k=key: self.show_view(k),
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[key] = btn

        tk.Frame(self.sidebar, bg="#111c33").pack(fill="both", expand=True)

        foot = tk.Frame(self.sidebar, bg="#111c33")
        foot.pack(fill="x", padx=16, pady=12)
        tk.Label(
            foot,
            text="SIMULATED DEMO\nNo real satellite link.",
            bg="#111c33",
            fg="#64748b",
            font=("Segoe UI", 8),
            justify="left",
        ).pack(anchor="w")

        self.content = ttk.Frame(self, style="App.TFrame")
        self.content.pack(side="left", fill="both", expand=True)

        self.views: dict[str, ttk.Frame] = {}
        self._build_dashboard_view()
        self._build_records_view()
        self._build_add_view()
        self._build_about_view()

    def _make_view(self, key: str) -> ttk.Frame:
        """Create (once) and return a content view frame."""
        if key not in self.views:
            frame = ttk.Frame(self.content, style="App.TFrame")
            self.views[key] = frame
        return self.views[key]

    # ------------------------------------------------------------------
    # Dashboard view
    # ------------------------------------------------------------------
    def _build_dashboard_view(self) -> None:
        view = self._make_view("dashboard")
        view.pack(fill="both", expand=True)

        header = ttk.Frame(view, style="App.TFrame")
        header.pack(fill="x", padx=22, pady=(20, 6))
        ttk.Label(header, text="Dashboard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Simulated mission status overview - demonstration data only.",
            style="Sub.TLabel",
        ).pack(anchor="w")

        cards_wrap = ttk.Frame(view, style="App.TFrame")
        cards_wrap.pack(fill="x", padx=22, pady=12)
        self.card_vars: dict[str, tk.StringVar] = {}

        for i, (key, label) in enumerate(
            [
                ("total", "Total Records"),
                ("satellites", "Satellites Tracked"),
                ("modes", "Modes In Use"),
                ("latest", "Latest Timestamp"),
            ]
        ):
            cards_wrap.columnconfigure(i, weight=1)
            card = ttk.Frame(cards_wrap, style="Card.TFrame", padding=16)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            ttk.Label(card, text=label, style="CardTitle.TLabel").pack(anchor="w")
            var = tk.StringVar(value="0")
            self.card_vars[key] = var
            ttk.Label(card, textvariable=var, style="CardValue.TLabel").pack(anchor="w")

        route_box = ttk.Frame(view, style="App.TFrame")
        route_box.pack(fill="x", padx=22, pady=(4, 10))
        ttk.Label(
            route_box,
            text="Autonomous Routing Demo (rule-based)",
            style="Section.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            route_box,
            text="Ranks the stored rows by signal strength, packet status and battery "
            "voltage. No trained AI model and no real radio link are involved.",
            style="Sub.TLabel",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(2, 6))
        ttk.Button(
            route_box,
            text="Simulate Routing Decision",
            style="Accent.TButton",
            command=self.run_route_demo,
        ).pack(anchor="w")
        self.route_label = ttk.Label(
            route_box,
            text="No routing decision computed yet.",
            style="Sub.TLabel",
            wraplength=900,
            justify="left",
        )
        self.route_label.pack(anchor="w", pady=(6, 0))

        ttk.Label(view, text="Recent Activity", style="Section.TLabel").pack(
            anchor="w", padx=22
        )
        recent_frame = ttk.Frame(view, style="App.TFrame")
        recent_frame.pack(fill="both", expand=True, padx=22, pady=(8, 22))
        self.recent_tree = self._make_tree(
            recent_frame,
            ("satellite_name", "timestamp", "mode", "signal_strength", "packet_status"),
            widths=(200, 190, 170, 140, 120),
        )


    # ------------------------------------------------------------------
    # Records view
    # ------------------------------------------------------------------
    def _build_records_view(self) -> None:
        view = self._make_view("records")
        view.pack(fill="both", expand=True)

        header = ttk.Frame(view, style="App.TFrame")
        header.pack(fill="x", padx=22, pady=(20, 6))
        ttk.Label(header, text="Mission Records", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Add, edit, delete, search and export stored telemetry rows.",
            style="Sub.TLabel",
        ).pack(anchor="w")

        bar = ttk.Frame(view, style="App.TFrame")
        bar.pack(fill="x", padx=22, pady=10)

        ttk.Label(bar, text="Search:", style="Field.TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=22)
        self.search_entry.pack(side="left", padx=(6, 16))

        ttk.Label(bar, text="Mode:", style="Field.TLabel").pack(side="left")
        self.mode_var = tk.StringVar(value="All Modes")
        self.mode_combo = ttk.Combobox(
            bar,
            textvariable=self.mode_var,
            values=["All Modes"] + MODES,
            state="readonly",
            width=22,
        )
        self.mode_combo.pack(side="left", padx=(6, 16))
        self.mode_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Button(bar, text="Apply", style="Accent.TButton", command=self.apply_filters).pack(
            side="left", padx=4
        )
        ttk.Button(bar, text="Clear", command=self.clear_filters).pack(side="left", padx=4)

        actions = ttk.Frame(view, style="App.TFrame")
        actions.pack(fill="x", padx=22, pady=(0, 8))
        ttk.Button(actions, text="Add Record", style="Accent.TButton", command=lambda: self.show_view("add")).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="Edit Selected", command=self.edit_selected).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Delete Selected", command=self.delete_selected).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Export CSV", command=self.export_csv).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Insert Demo Data", command=self.insert_demo_data).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Refresh", command=self.refresh_all).pack(side="left", padx=6)

        table_frame = ttk.Frame(view, style="App.TFrame")
        table_frame.pack(fill="both", expand=True, padx=22, pady=(0, 22))
        self.tree = self._make_tree(
            table_frame,
            COLS[1:],
            widths=(150, 165, 150, 110, 120, 100, 110, 200),
            stretch=(False, False, False, False, False, False, False, True),
        )
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    def _make_tree(self, parent, columns, widths, stretch=None) -> ttk.Treeview:
        """Create a styled scrollable table and return the Treeview."""
        tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            style="Data.Treeview",
            selectmode="browse",
        )
        for i, (col, width) in enumerate(zip(columns, widths)):
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(
                col,
                width=width,
                anchor="w",
                stretch=stretch[i] if stretch else False,
            )
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return tree


    # ------------------------------------------------------------------
    # Add / Edit form
    # ------------------------------------------------------------------
    def _build_add_view(self) -> None:
        view = self._make_view("add")
        view.pack(fill="both", expand=True)

        header = ttk.Frame(view, style="App.TFrame")
        header.pack(fill="x", padx=22, pady=(20, 6))
        self.form_title = ttk.Label(header, text="Add Mission Record", style="Title.TLabel")
        self.form_title.pack(anchor="w")
        ttk.Label(
            header,
            text="Fields marked * are required. Values are stored locally in SQLite.",
            style="Sub.TLabel",
        ).pack(anchor="w")

        form = ttk.Frame(view, style="App.TFrame")
        form.pack(fill="x", padx=22, pady=10)

        self.field_vars: dict[str, tk.StringVar] = {
            "satellite_name": tk.StringVar(),
            "timestamp": tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "mode": tk.StringVar(value=MODES[0]),
            "battery_voltage": tk.StringVar(),
            "signal_strength": tk.StringVar(),
            "temperature": tk.StringVar(),
            "packet_status": tk.StringVar(value="1"),
            "notes": tk.StringVar(),
        }

        rows = [
            ("Satellite Name *", "satellite_name"),
            ("Timestamp *", "timestamp"),
            ("Communication Mode *", "mode"),
            ("Battery Voltage (V)", "battery_voltage"),
            ("Signal Strength (dBm)", "signal_strength"),
            ("Temperature (C)", "temperature"),
            ("Packet Status (0=OK 1=Warning 2=Critical)", "packet_status"),
            ("Notes", "notes"),
        ]

        for i, (label, key) in enumerate(rows):
            form.columnconfigure(1, weight=1)
            ttk.Label(form, text=label, style="Field.TLabel").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=6
            )
            if key == "mode":
                widget = ttk.Combobox(
                    form, textvariable=self.field_vars[key], values=MODES, state="readonly"
                )
            elif key == "notes":
                widget = ttk.Entry(form, textvariable=self.field_vars[key], width=60)
            else:
                widget = ttk.Entry(form, textvariable=self.field_vars[key], width=40)
            widget.grid(row=i, column=1, sticky="w", pady=6)

        buttons = ttk.Frame(view, style="App.TFrame")
        buttons.pack(fill="x", padx=22, pady=6)
        ttk.Button(buttons, text="Save Record", style="Accent.TButton", command=self.save_record).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(buttons, text="Clear Form", command=self.clear_form).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=lambda: self.show_view("records")).pack(
            side="left", padx=6
        )

        self.form_status = ttk.Label(view, text="", style="Sub.TLabel")
        self.form_status.pack(anchor="w", padx=22, pady=(6, 20))


    # ------------------------------------------------------------------
    # About view
    # ------------------------------------------------------------------
    def _build_about_view(self) -> None:
        view = self._make_view("about")
        view.pack(fill="both", expand=True)

        header = ttk.Frame(view, style="App.TFrame")
        header.pack(fill="x", padx=22, pady=(20, 6))
        ttk.Label(header, text="About / Help", style="Title.TLabel").pack(anchor="w")

        body = tk.Frame(view, bg="#0f172a")
        body.pack(fill="both", expand=True, padx=22, pady=10)

        text = (
            "SomaiyaSat & SomaiyaPod - Mission Dashboard\n"
            "==============================================\n\n"
            "A college Python lab mini-project built with Tkinter/ttk and SQLite.\n\n"
            "WHAT THIS APP REALLY DOES\n"
            "  * Stores, searches, edits, deletes and exports mission records.\n"
            "  * Creates the SQLite database automatically on the first run.\n\n"
            "WHAT THIS APP DOES *NOT* DO (please be clear in your viva)\n"
            "  * It does NOT talk to any real satellite or ground station.\n"
            "  * It does NOT transmit, receive or decode M17, Codec2 or SSTV.\n"
            "  * It does NOT run a trained AI or machine-learning model.\n"
            "    The 'routing' feature is a small, transparent rule-based demo\n"
            "    that ranks stored rows by signal, packet status and battery.\n"
            "  * All telemetry shown is simulated sample data.\n\n"
            "HOW TO USE\n"
            "  1. Dashboard  - summary cards, recent activity, routing demo.\n"
            "  2. Records   - full table with search, mode filter and CSV export.\n"
            "  3. Add Record- validated form for a new telemetry row.\n"
            "  4. About     - this help text.\n\n"
            "Keyboard / mouse: double-click a table row to edit it."
        )
        tk.Label(
            body,
            text=text,
            bg="#0f172a",
            fg="#e2e8f0",
            font=("Consolas", 10),
            justify="left",
            anchor="nw",
        ).pack(fill="both", expand=True, padx=6, pady=6)

    # ------------------------------------------------------------------
    # Navigation + refreshing
    # ------------------------------------------------------------------
    def show_view(self, key: str) -> None:
        """Show one content view and hide the others."""
        self.current_view = key
        for name, frame in self.views.items():
            if name == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        if key == "add" and self.selected_id is None:
            self.clear_form()
        self.refresh_all()

    def refresh_all(self) -> None:
        """Reload the dashboard cards and both tables from the database."""
        try:
            self._refresh_dashboard()
            self._refresh_table()
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", f"Could not read the database:\n{exc}")

    def _refresh_dashboard(self) -> None:
        total = self.db.count()
        self.card_vars["total"].set(str(total))

        records = self.db.all_records()
        names = {r[1] for r in records}
        modes = {r[3] for r in records}
        self.card_vars["satellites"].set(str(len(names)))
        self.card_vars["modes"].set(str(len(modes)))
        self.card_vars["latest"].set(records[0][2] if records else "-")

        self.recent_tree.delete(*self.recent_tree.get_children())
        for row in self.db.recent(5):
            self.recent_tree.insert(
                "",
                "end",
                values=(row[1], row[2], row[3], row[5], row[7]),
            )


    def _refresh_table(self) -> None:
        """Fill the main table using the current search text and mode filter."""
        self.tree.delete(*self.tree.get_children())
        satellite = self.search_var.get().strip()
        mode = self.mode_var.get()
        if mode == "All Modes":
            mode = ""

        rows = self.db.search(satellite, mode)
        for row in rows:
            self.tree.insert(
                "",
                "end",
                iid=str(row[0]),
                values=(
                    row[1],
                    row[2],
                    row[3],
                    "" if row[4] is None else row[4],
                    "" if row[5] is None else row[5],
                    "" if row[6] is None else row[6],
                    row[7],
                    row[8] or "",
                ),
            )

    # ------------------------------------------------------------------
    # Search and filter
    # ------------------------------------------------------------------
    def apply_filters(self) -> None:
        """Apply the search box and the mode drop-down to the table."""
        self._refresh_table()

    def clear_filters(self) -> None:
        """Reset the search box and the mode drop-down."""
        self.search_var.set("")
        self.mode_var.set("All Modes")
        self._refresh_table()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate(self) -> tuple | None:
        """Validate the form.

        Returns a ready-to-store tuple, or None when something is wrong
        (an error box is shown before returning None).
        """
        name = self.field_vars["satellite_name"].get().strip()
        if not name:
            messagebox.showwarning("Missing field", "Satellite name is required.")
            return None

        stamp = self.field_vars["timestamp"].get().strip()
        if not stamp:
            messagebox.showwarning("Missing field", "Timestamp is required.")
            return None

        mode = self.field_vars["mode"].get().strip()
        if mode not in MODES:
            messagebox.showwarning("Invalid mode", "Please choose a valid communication mode.")
            return None

        voltage = self._read_number(
            "Battery voltage", self.field_vars["battery_voltage"], MIN_VOLTAGE, MAX_VOLTAGE
        )
        if voltage is _INVALID:
            return None

        signal = self._read_number(
            "Signal strength", self.field_vars["signal_strength"], MIN_SIGNAL, MAX_SIGNAL
        )
        if signal is _INVALID:
            return None

        temperature = self._read_number(
            "Temperature", self.field_vars["temperature"], MIN_TEMP, MAX_TEMP
        )
        if temperature is _INVALID:
            return None

        status_text = self.field_vars["packet_status"].get().strip()
        try:
            status = int(status_text)
        except ValueError:
            messagebox.showwarning(
                "Invalid packet status", "Packet status must be 0, 1 or 2."
            )
            return None
        if status not in (0, 1, 2):
            messagebox.showwarning(
                "Invalid packet status", "Packet status must be 0, 1 or 2."
            )
            return None

        notes = self.field_vars["notes"].get().strip()
        return (name, stamp, mode, voltage, signal, temperature, status, notes)

    def _read_number(self, label: str, var: tk.StringVar, low: float, high: float):
        """Read an optional number field and check that it is in range."""
        raw = var.get().strip()
        if raw == "":
            return None
        try:
            value = float(raw)
        except ValueError:
            messagebox.showwarning(
                "Invalid number", f"{label} must be a number (got '{raw}')."
            )
            return _INVALID
        if not (low <= value <= high):
            messagebox.showwarning(
                "Out of range", f"{label} must be between {low} and {high}."
            )
            return _INVALID
        return value


    # ------------------------------------------------------------------
    # Record actions
    # ------------------------------------------------------------------
    def clear_form(self) -> None:
        """Reset every field on the add/edit form."""
        self.field_vars["satellite_name"].set("")
        self.field_vars["timestamp"].set(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.field_vars["mode"].set(MODES[0])
        self.field_vars["battery_voltage"].set("")
        self.field_vars["signal_strength"].set("")
        self.field_vars["temperature"].set("")
        self.field_vars["packet_status"].set("1")
        self.field_vars["notes"].set("")
        self.form_title.config(text="Add Mission Record")
        self.form_status.config(text="")

    def save_record(self) -> None:
        """Validate the form and save it (insert a new row, or update one)."""
        data = self._validate()
        if data is None:
            return
        try:
            if self.selected_id is None:
                self.db.insert(data)
                action = "saved"
            else:
                self.db.update((*data, self.selected_id))
                action = "updated"
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", f"Could not save the record:\n{exc}")
            return
        self.selected_id = None
        self.clear_form()
        self.refresh_all()
        self.show_view("records")
        messagebox.showinfo("Saved", f"The mission record was {action}.")

    def _selected_row(self):
        """Return the selected table row id, or None."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Nothing selected", "Please select a row in the table first."
            )
            return None
        return int(selection[0])

    def edit_selected(self) -> None:
        """Load the selected row into the form and open it for editing."""
        row_id = self._selected_row()
        if row_id is None:
            return
        rows = self.db.all_records()
        match = next((r for r in rows if r[0] == row_id), None)
        if match is None:
            messagebox.showerror("Error", "That record no longer exists.")
            self.refresh_all()
            return

        self._fill_form_from(match)
        self.selected_id = row_id
        self.show_view("add")
        # show_view() may reset the form, so re-apply the loaded values.
        self._fill_form_from(match)
        self.form_title.config(text=f"Edit Mission Record #{row_id}")
        self.form_status.config(text=f"Editing record id {row_id}.")

    def _fill_form_from(self, match) -> None:
        """Copy a database row into the form fields."""
        self.field_vars["satellite_name"].set(match[1])
        self.field_vars["timestamp"].set(match[2])
        self.field_vars["mode"].set(match[3])
        self.field_vars["battery_voltage"].set("" if match[4] is None else match[4])
        self.field_vars["signal_strength"].set("" if match[5] is None else match[5])
        self.field_vars["temperature"].set("" if match[6] is None else match[6])
        self.field_vars["packet_status"].set(str(match[7]))
        self.field_vars["notes"].set(match[8] or "")

    def delete_selected(self) -> None:
        """Delete the selected row after asking the user to confirm."""
        row_id = self._selected_row()
        if row_id is None:
            return
        rows = self.db.all_records()
        match = next((r for r in rows if r[0] == row_id), None)
        if match is None:
            messagebox.showerror("Error", "That record no longer exists.")
            self.refresh_all()
            return
        confirmed = messagebox.askyesno(
            "Confirm delete",
            f"Delete this record?\n\n"
            f"Satellite : {match[1]}\n"
            f"Timestamp : {match[2]}\n"
            f"Mode     : {match[3]}\n\n"
            "This cannot be undone.",
            icon="warning",
        )
        if not confirmed:
            return
        try:
            self.db.delete(row_id)
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", f"Could not delete the record:\n{exc}")
            return
        self.selected_id = None
        self.refresh_all()
        messagebox.showinfo("Deleted", "The record was deleted.")


    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------
    def export_csv(self) -> None:
        """Ask for a file name and write the stored records to a CSV file."""
        if filedialog is None:
            messagebox.showerror("Unavailable", "The file dialog is not available.")
            return
        default_name = f"somaiya_missions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export mission records to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_name,
        )
        if not path:
            return  # the user pressed Cancel
        try:
            self.db.export_to_csv(path)
        except (OSError, sqlite3.Error) as exc:
            messagebox.showerror(
                "Export failed", f"Could not write the CSV file:\n{exc}"
            )
            return
        messagebox.showinfo("Export complete", f"Records exported to:\n{path}")

    # ------------------------------------------------------------------
    # Demo data and routing demo
    # ------------------------------------------------------------------
    def insert_demo_data(self) -> None:
        """Insert clearly labelled demonstration records."""
        confirmed = messagebox.askyesno(
            "Insert demo data",
            "This will insert 4 clearly labelled DEMO records plus 4 simulated "
            "telemetry rows into the database.\n\n"
            "All of them are fake demonstration data, not real flight data.\n\n"
            "Do you want to continue?",
        )
        if not confirmed:
            return
        demo_rows = list(DEFAULT_DEMO_RECORDS) + generate_demo_records(4)
        try:
            for record in demo_rows:
                self.db.insert(record)
        except sqlite3.Error as exc:
            messagebox.showerror(
                "Database error", f"Could not insert the demo records:\n{exc}"
            )
            return
        self.refresh_all()
        messagebox.showinfo(
            "Demo data inserted",
            f"{len(demo_rows)} demo records were inserted. Look for names such "
            "as 'SomaiyaSat-1 [DEMO]' and 'SomaiyaPod-2 [DEMO]'.",
        )

    def run_route_demo(self) -> None:
        """Run the transparent rule-based routing demonstration."""
        rows = self.db.all_records()
        if not rows:
            self.route_label.config(text="No records stored yet - add some first.")
            return
        self.route_ids = compute_route(rows)
        best = next((r for r in rows if r[0] == self.route_ids[0]), None)
        if best is None:
            self.route_label.config(text="Could not compute a route.")
            return
        summary = (
            f"Recommended downlink (rule-based): {best[1]} via {best[3]} - "
            f"signal {best[5]} dBm, status {best[7]}, battery {best[4]} V. "
            f"Alternatives: {len(self.route_ids) - 1}. "
            "Reminder: this is a simulated demo, not real AI or radio."
        )
        self.route_label.config(text=summary)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Create the database if needed, then open the window."""
    try:
        App().mainloop()
    except sqlite3.Error as exc:
        print(f"Database error: {exc}")
    except OSError as exc:
        print(f"File system error: {exc}")


if __name__ == "__main__":
    main()

