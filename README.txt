
# LifeStream — Blood Donation Management System
## Django Web Application — Setup & Run Guide

Islamic University | Faculty of Computer and Information Systems
Software Engineering Project — 2nd Semester 2026
Ahmad Ibn Abdul-Samie Wongrawa (443050183) | Alhassan Dedach (441038833)

---

## STEP-BY-STEP SETUP (do this ONCE on a new machine)

### Step 1 — Make sure Python is installed
Open a terminal (Command Prompt or PowerShell on Windows) and run:
    python --version
You need Python 3.10 or newer. Download from https://python.org if needed.

### Step 2 — Extract the ZIP file
Extract LifeStream_Django_App.zip into a folder, e.g.:
    C:\Projects\LifeStream\      (Windows)
    ~/Desktop/LifeStream/        (Mac/Linux)

### Step 3 — Install Django
In your terminal, run:
    pip install django pillow

### Step 4 — Go into the project folder
    cd path/to/LifeStream

### Step 5 — Run database migrations (sets up all tables)
    python manage.py migrate

### Step 6 — Seed the database (creates all demo accounts and data)
    python manage.py seed

### Step 7 — Start the server
    python manage.py runserver

### Step 8 — Open in your browser
    http://127.0.0.1:8000

That is it. The application is running.

---

## LOGIN ACCOUNTS (for the exhibition demo)

| Role            | Username      | Password  | What they can do                          |
|-----------------|---------------|-----------|-------------------------------------------|
| Administrator   | admin         | admin123  | Full system access, reports, all data     |
| Donor           | ahmed_donor   | demo123   | Receive alerts, record donations          |
| Donor           | fatima_donor  | demo123   | Blood type A+, available                  |
| Donor           | khalid_donor  | demo123   | Blood type O- (universal donor)           |
| Patient         | patient1      | demo123   | Submit requests, track status             |
| Patient         | patient2      | demo123   | Active pending request in system          |
| Hospital Staff  | staff1        | demo123   | Manage inventory at King Fahd Hospital    |

---

## EXHIBITION DEMO SCRIPT

### Demo 1 — Admin Overview (login: admin / admin123)
- Show the admin dashboard: donor count, open requests, blood stock summary
- Go to Reports → show blood type supply table with colour-coded status
- Go to User Management → show all roles, filter by donor
- Go to Hospital Management → show registered hospitals

### Demo 2 — Patient submits a blood request (login: patient1 / demo123)
- Click "Submit New Blood Request"
- Select blood type: O+, quantity: 2, urgency: Critical
- Submit → system either finds stock (shows matched) or alerts donors
- Copy the reference number shown

### Demo 3 — Track a request WITHOUT logging in
- Click "Track Request" in the top navbar (no login needed)
- Paste any reference number (e.g. from Demo 2) → shows real-time status

### Demo 4 — Donor receives notification (login: ahmed_donor / demo123)
- Dashboard shows pending blood alerts
- Click "View My Notifications"
- Click "I'm Available" → request status updates to "Donor Committed"

### Demo 5 — Hospital Staff updates inventory (login: staff1 / demo123)
- Dashboard shows current King Fahd Hospital stock
- Click "Blood Inventory" → update an O+ quantity
- Drop it below 5 → see "Critically Low" warning appear

### Demo 6 — Search blood (no login needed)
- Go to http://127.0.0.1:8000/search/
- Search: blood type = A+, city = Jeddah
- See which hospitals have stock and how much

---

## SYSTEM FEATURES SUMMARY

Phase 1 — All requirements implemented:
  FR-01  Registration and login for all 4 roles
  FR-02  Donor profile management (blood type, availability, city)
  FR-03  Patient blood request submission with urgency levels
  FR-04  Blood search by type and city (public, no login)
  FR-05  Automatic donor notification when blood is urgently needed
  FR-06  Admin blood inventory management
  FR-07  Admin user account management (activate/deactivate)
  FR-08  Hospital staff inventory updates with critical-low alerts
  FR-09  Hospital staff request status management
  FR-10  Admin reports and analytics dashboard
  FR-11  Public request tracking by reference number (no login)

Phase 2 — Architecture:
  Three-Tier Layered Architecture + MVC Pattern
  Presentation: Django templates (HTML5/Bootstrap 5)
  Application:  Django views (controllers) + forms + services
  Data:         SQLite database via Django ORM (matches Class Diagram exactly)

Phase 3 — Implementation:
  7 database models: User, Hospital, Inventory, BloodRequest, Notification, Donation, AuditLog
  25 URL routes covering all use cases
  Role-based access control on every protected view
  Audit logging for all sensitive admin actions

---

## FILE STRUCTURE

lifestream/          Django project settings and main URL config
core/
  models.py          All 7 database models (matches Class Diagram)
  views.py           All 25 view functions (matches Sequence Diagrams)
  forms.py           All user-facing forms
  urls.py            All URL routes
  admin.py           Django admin panel registration
  management/
    commands/
      seed.py        Demo data seeding command
  migrations/        Database migration files
templates/
  base.html          Master layout with sidebar navigation
  core/              All 18 HTML templates (one per page)
static/              CSS and JS assets

---

## TECHNOLOGY STACK
  Backend:   Python 3.10 + Django 5.x
  Database:  SQLite (file: lifestream.db)
  Frontend:  Bootstrap 5.3 + Bootstrap Icons
  ORM:       Django ORM (maps directly to UML Class Diagram)
