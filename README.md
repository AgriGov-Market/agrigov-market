# AgriGov Market

AgriGov Market is a Django app for ministry-managed agricultural product listings, buyer orders, and transporter delivery tracking.

## Requirements

- Python 3.12 recommended
- `pip`

## Setup

1. Clone the repository.
2. Open a terminal in the project folder.
3. Create a virtual environment:

```powershell
python -m venv venv
```

4. Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the environment Python directly in the commands below.

5. Install dependencies:

```powershell
pip install -r requirements.txt
```

6. Apply migrations:

```powershell
python manage.py migrate
```

7. Run the server:

```powershell
python manage.py runserver
```

8. Open the app:

- App: `http://127.0.0.1:8000/`
- Django admin: `http://127.0.0.1:8000/admin/`

## Admin Login

Current app admin account:

- Username: `ministryofagriculture`
- Password: `AgriGov2026!`

## Alternative Without Activating venv

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```
