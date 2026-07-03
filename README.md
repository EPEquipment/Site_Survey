# EP Equipment – Smart Products Site Survey Tool

A [Streamlit](https://streamlit.io) web app used by EP Equipment sales engineers during presales site visits. It collects customer/site requirements for AGV/AMR projects, validates the requested configuration against product specs live, calculates a recommended fleet size, and generates a structured Word (`.docx`) report bundled with all attachments into a downloadable ZIP.

🌐 **Live app:** [ep-intelligent-survey-tool.streamlit.app](https://ep-intelligent-survey-tool.streamlit.app)

---

## What it does

- **4-tab survey form**: Basic Information → Material Flow → Data Flow & Integration → Site Conditions & Safety
- **Two view modes**: *Expert* (all 4 tabs visible at once) or *Guided* (one step at a time, with Back/Next navigation and a progress bar) — toggled in the sidebar
- **7 languages**: English, Deutsch, Français, Nederlands, Español, Italiano, Polski (`translations.py`)
- **Live product validation**: real-time ✅ / ⚠️ / ❌ checks against the actual EP layout-planning specs for:
  - **XPL201** (Transport / Cross Docking) — up to 2000 kg, floor level, min. 1.5 m aisle
  - **XQE122** (Stacking / Conveyor) — up to 1500 kg, up to 5.5 m lift, min. 2900 mm aisle
  - **XNA121 / XNA151** (Narrow Aisle) — up to 1200 / 1500 kg, up to 8.5 m / 13 m lift, min. 1.78 m aisle
- **Fleet size estimation**: derives cycle time from average transport distance and per-product speed, then estimates the number of vehicles needed from required throughput (pallets/hour)
- **Smart defaults**: pre-fills typical values once an application type is selected
- **Word report generation**: fills `template.docx` (Jinja2 placeholders via `docxtpl`) with all collected data, validation results, and recommendations
- **ZIP packaging & auto-download**: the generated `.docx`, any uploaded CAD/layout files, conveyor pictures, and site photos are zipped together and downloaded automatically in the browser
- **Save / Resume session**: export the entire form state as a `.json` file and reload it later (uploaded files themselves are not persisted, only form field values)
- **Resource library**: in-app download buttons for layout specs, customer white books, and system requirement PDFs (see `RESOURCES` in `app.py`)

---

## Products covered

| Product | Application | Max Weight | Max Height | Min Aisle |
|---|---|---|---|---|
| XPL201 | Transport / Cross Docking | 2000 kg (Euro pallet structural limit ~1500 kg) | Floor level | 1.5 m |
| XQE122 | Stacking / Conveyor | 1500 kg | 5.5 m | 2900 mm |
| XNA121 | Narrow Aisle | 1200 kg | 8.5 m | 1.78 m |
| XNA151 | Narrow Aisle | 1500 kg | 13.0 m | 1.78 m |

Full specs and validation logic live in [products.py](products.py) and [product_validators.py](product_validators.py).

---

## Project structure

```
app.py                  Main entrypoint: page setup, sidebar (language/mode/session save-load),
                         resource library, report/ZIP generation, auto-download
header_tab.py           Tab 1 — Basic Information: customer details, application type, pallet
                         config, inline product validation
secondary_tab.py        Tab 2 — Material Flow: process/route sequence builder, distances, photos
data_flow_tab.py        Tab 3 — Data Flow & Integration: system architecture / integration block builder
site_conditions_tab.py  Tab 4 — Site Conditions & Safety
product_validators.py   XPL201 / XQE122 / XNA121-151 validation rules (weight, height, aisle width)
products.py             Full product spec catalogue (dimensions, aisle tables, charging stations, etc.)
translations.py         UI strings for all 7 supported languages
template.docx           Word report template (Jinja2 placeholders, rendered via docxtpl)
template.docx.backup    Backup copy of the template
reports/                Sample/previously generated .docx reports (not required to run the app)
requirements.txt        Python dependencies
run_app.bat             Windows launcher — activates the local venv and runs the app
.devcontainer/           GitHub Codespaces / VS Code Dev Container config
```

---

## Running locally (Windows)

The project already has a local virtual environment folder named `gradio-survey` (despite the name, it's a plain Python 3.13 venv for this Streamlit app, not a Gradio project).

**Option A — use the existing venv and the batch launcher**

```bat
run_app.bat
```

This activates `.\gradio-survey\Scripts\activate.bat` and runs the app with the venv's Python.

**Option B — manual / fresh environment**

```powershell
python -m venv gradio-survey
.\gradio-survey\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

> Note: `run_app.bat` currently ends with `.\gradio-survey\Scripts\python.exe app.py` — running `app.py` directly with Python (instead of `streamlit run app.py`) will not start the Streamlit server correctly. If the batch file doesn't launch the UI, run `streamlit run app.py` manually from the activated venv instead.

### Running on macOS/Linux (or Codespaces)

```bash
pip install -r requirements.txt
streamlit run app.py
```

The included `.devcontainer/devcontainer.json` does this automatically for GitHub Codespaces / VS Code Dev Containers, forwarding port `8501`.

---

## Requirements

From [requirements.txt](requirements.txt):

```
streamlit>=1.32.0
docxtpl>=0.16.0
python-docx>=1.1.0
```

Requires Python 3.11+ (the local venv uses 3.13).

---

## Deployment

### Streamlit Community Cloud (current production deployment)

The live app is hosted on **Streamlit Community Cloud** (free tier), connected to this repo's `main` branch.

- Every push to `main` triggers an automatic redeploy (~30 seconds).
- To deploy your own copy: push this repo to GitHub, then go to [share.streamlit.io](https://share.streamlit.io) → "New app" → point it at the repo, branch `main`, main file `app.py`.
- No extra secrets/config are required — the app is self-contained (no external API keys).

### Alternative hosting (Render / Railway / any Python host)

The app has no server-specific code, so it can run on any host that can run `streamlit run app.py` behind a reverse proxy:

```
Build command: pip install -r requirements.txt
Start command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

### Docker

There's no Dockerfile in the repo yet, but a minimal one would look like:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### GitHub Codespaces / Dev Container

Open the repo in a Codespace (or "Reopen in Container" in VS Code) — `.devcontainer/devcontainer.json` installs `requirements.txt` and auto-starts `streamlit run app.py` on port 8501 with a forwarded preview.

---

## Notes on data & files

- Uploaded files (CAD/layout, conveyor pictures, site photos) exist only in-memory for the session and are packaged into the ZIP at report-generation time — they are **not** written to disk or persisted between sessions.
- The `reports/` folder in this repo contains example previously-generated reports; it isn't required for the app to function and can be cleared safely.
- Saved session `.json` files store form field values only (not uploaded file contents), so files must be re-attached after reloading a session.

---

## Contact

EP Equipment EU — [ep-equipment.eu](https://ep-equipment.eu)
