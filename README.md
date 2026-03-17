# Digital Queue Prototype (IS-211)

Simple Python prototype for a **two-queue** ticket system (regular + priority) with:
- Issue ticket (customer kiosk)
- Call next customer (staff)
- Public display screen (now serving + counts)
- Reset to 0 (new day / closing)
- No database (optional local `state.json` file)

## Run locally

### Install

From this folder (`C:\Users\arild\queue-prototype`), install dependencies:

```bash
pip install -r requirements.txt
```

### Start (recommended on Windows / PowerShell)

```powershell
python -m streamlit run app.py --server.headless true --server.showEmailPrompt false
```

Then open `http://localhost:8501`.

### Start (if `streamlit` is on PATH)

```bash
streamlit run app.py
```

## Data structures & complexity (for your report)

- **Queue**: `collections.deque` for `priority` and `regular`
  - `issue_ticket()` appends to a deque in **O(1)**
  - `call_next()` pops from a deque in **O(1)**
- **Hash table**: Python `dict` for ticket lookup by number
  - storing/fetching tickets is **O(1)** average
- **Intentional O(n)** example for analysis:
  - `position_and_eta(ticket_number)` scans the deque(s) to find the ticket index in **O(n)**

## Reset behavior

- Automatic: resets if a new calendar day is detected.
- Manual: use **Reset** in the sidebar (also sets counter back to 0).

