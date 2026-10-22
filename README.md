# SomaiyaSat & SomaiyaPod — Mission Dashboard

A beginner-friendly Python desktop mini-project for a college Python lab.

**Project topic:** *SomaiyaSat & SomaiyaPod: A PocketQube Mission featuring
Autonomous AI-Based Inter-Satellite Data Routing and Advanced Multi-Mode
Amateur Radio Payloads (M17, Codec2, SSTV, & TT&C / Housekeeping).*

Built with **Python + Tkinter/ttk** for the GUI and **SQLite** for storage.
Standard library only — no PostgreSQL, no server, no `pip install` needed.

---

## ⚠️ Honesty note (please read this before your viva)

This is a **desktop demonstration project**. It is honest about what it does:

| The app **does** | The app **does not** do |
| --- | --- |
| Store, search, edit, delete and export mission records in SQLite | ❌ Communicate with any real satellite or ground station |
| Show summary cards, a data table and recent activity | ❌ Transmit, receive or decode M17 / Codec2 / SSTV radio signals |
| Run a small, **transparent, rule-based** routing demo | ❌ Run a trained AI or machine-learning model |
| Insert clearly labelled `[DEMO]` sample telemetry | ❌ Contain real flight data — everything shown is simulated |

The "AI-based inter-satellite data routing" feature is a **simple ranking
function** (`compute_route()`), not a neural network. Every demo row is tagged
`[DEMO]` so it can never be mistaken for real telemetry.

**In your viva, say clearly:** *"The telemetry is simulated and the AI is a
rule-based demo — the app is a GUI/CRUD and data-visualisation project, not a
real satellite ground station."*

---

## Features

1. **Dashboard** — summary cards (total records, satellites tracked, modes in
   use, latest timestamp), a Recent Activity table, and the routing demo.
2. **Mission records** — full **add / view / edit / delete** (CRUD) support.
3. **Telemetry fields** — satellite name, timestamp, communication mode
   (M17 / Codec2 / SSTV / TT&C & Housekeeping), battery voltage, signal
   strength, temperature, packet status and notes.
4. **Search & filtering** — free-text search by satellite name plus a
   communication-mode drop-down; the two combine.
5. **Validation** — empty required fields and out-of-range numeric readings
   are rejected with a clear message; deletion always asks for confirmation.
6. **CSV export** — export every stored record through a save-file dialog.
7. **Modern ttk interface** — sidebar navigation, summary cards, styled data
   tables and clearly labelled buttons.
8. **Sample data** — one button inserts 8 clearly labelled demonstration rows.
9. **Reliability** — every DB call uses `try / finally` so the SQLite
   connection always closes; database and file errors are caught and shown in
   a message box instead of crashing; the dashboard and table refresh after
   every change.
10. **Documentation** — this `README.md`.


---

## How to run

1. Install Python 3.9+ from <https://www.python.org/downloads/> and tick
   **"Add Python to PATH"** during installation.
2. Open a terminal in this folder (`Shift + Right-click → Open in Terminal`,
   or `cd` into it).
3. Run:

   ```
   python main.py
   ```

   On some systems the command is `python3 main.py`.

There is nothing else to install — Tkinter ships with Python on Windows and
macOS. On Debian/Ubuntu you may need `sudo apt install python3-tk`.

The SQLite database `missions.db` is **created automatically** in this folder
the first time you run the app.

---

## Project structure

```
SomaiyaSat_Mission_Dashboard/
├── main.py        # the complete application (single file)
├── missions.db    # created automatically on first run
├── README.md      # this documentation
└── __pycache__/   # created automatically by Python (safe to delete)
```

---

## Database design

One table, `missions`, is created with `CREATE TABLE IF NOT EXISTS`, so the
first run and every later run behave the same.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER | Primary key, auto-increment |
| `satellite_name` | TEXT | **NOT NULL** — required |
| `timestamp` | TEXT | **NOT NULL** — required, `YYYY-MM-DD HH:MM:SS` |
| `mode` | TEXT | **NOT NULL** — one of the four modes |
| `battery_voltage` | REAL | Optional, volts |
| `signal_strength` | REAL | Optional, dBm (negative) |
| `temperature` | REAL | Optional, °C |
| `packet_status` | INTEGER | **NOT NULL** — 0 = OK, 1 = Warning, 2 = Critical |
| `notes` | TEXT | Optional, free text |

All SQL uses **parameterised queries** (`?` placeholders), so user input is
never glued into a SQL string.

### Validation ranges

| Field | Accepted range | Why |
| --- | --- | --- |
| Battery voltage | 2.5 – 4.5 V | Plausible PocketQube/amateur payload bus |
| Signal strength | −120 – −30 dBm | Typical amateur band receive range |

---

## How the code is organised

`main.py` is one file, but it is split into clearly labelled sections that
are easy to explain one by one:

| Section | What it holds |
| --- | --- |
| Module docstring | Project intro + the honesty note |
| Imports | Python standard library only |
| Configuration constants | `COLS`, `MODES`, `DEFAULT_DEMO_RECORDS`, validation limits |
| `class Database` | All SQLite access — `insert`, `update`, `delete`, `search`, `export_to_csv`… |
| `generate_demo_records()` | Builds simulated telemetry rows |
| `compute_route()` | The rule-based routing demo |
| `class App(tk.Tk)` | The GUI: styles, layout, views, actions |
| `main()` | Entry point |

Two beginner-friendly ideas are used throughout:

* **The `Database` class owns all SQL.** The GUI never writes SQL, so the two
  halves of the program are easy to explain separately.
* **Every DB method uses `try: ... finally: conn.close()`.** The `finally`
  block runs even if something fails, so the SQLite connection is *always*
  released — no file locks, no "database is locked" errors.

---

## Features to test (a good viva demo order)

1. **First run** — start the app; `missions.db` appears in the folder and the
   dashboard shows `0` records.
2. **Sample data** — click *Insert Demo Data* → confirm → 8 rows appear, all
   tagged `[DEMO]`. The dashboard cards update to `8` records.
3. **Search** — type `SomaiyaSat` in the search box and press *Apply*; only
   matching rows remain. Press *Clear* to restore them.
4. **Filter** — pick `SSTV` in the Mode drop-down; only SSTV rows remain.
   Combine it with the search box to show both filters work together.
5. **Add** — *Add Record*, leave the satellite name empty and save → a
   warning appears and nothing is saved. Enter `abc` as battery voltage → it
   is rejected. Enter `99` → rejected as out of range. Fill the form
   correctly and save → the row appears in the table.
6. **Edit** — select a row, press *Edit Selected* (or double-click it),
   change a value, save → the row updates and the count stays the same.
7. **Delete** — select a row, press *Delete Selected* → a confirmation dialog
   appears. Cancel first (nothing happens), then confirm → the row disappears
   and the total decreases.
8. **CSV export** — press *Export CSV*, choose a location, then open the file
   in a text editor or Excel to confirm the rows were written.
9. **Routing demo** — on the Dashboard press *Simulate Routing Decision*; the
   app names the best row by signal strength, packet status and battery.
   Explain that it is a rule, not AI.
10. **Persistence** — close the app and start it again; the records are still
    there (that is the point of using SQLite).
11. **About** — open *About / Help* to show the honesty note on screen.

---

## Limitations

* **Simulation only.** No satellite, radio, modem or network link exists.
* **The "AI" is a rule-based ranking**, not a trained model. There is no
  machine-learning library involved.
* **No M17 / Codec2 / SSTV encoding or decoding.** The mode is stored as a
  text label so the four payload modes can be demonstrated and filtered.
* **Single-user desktop app.** No login, no multi-user support, no network
  access.
* **Plain-text timestamps.** They are stored as strings in
  `YYYY-MM-DD HH:MM:SS` format for readability; sorting works because that
  format sorts chronologically, but a production app would use a proper
  date type.
* **The table shows all rows.** There is no pagination, so a very large
  database would slow the UI down.
* **The CSV export writes every row**, not just the rows matching the current
  search or filter.
* **Delete has no undo.** The confirmation dialog is the only safeguard.
* **Windows/Linux/macOS** desktop only — it is not a web app and cannot be
  deployed to a phone.

---

## Possible future extensions

* A separate `routes` table to store the routing decisions over time.
* Matplotlib charts of battery voltage and signal strength over time.
* Import records from an existing CSV file.
* A "simulation mode" that keeps generating new demo telemetry every few
  seconds so the dashboard feels live.

| Temperature | −40 – 85 °C | Plausible satellite component range |
| Packet status | 0, 1 or 2 | Matches the three status labels |
