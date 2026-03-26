# 🏛️ Campus Issues Reporting System (CIRS)
### CDGI Indore — Minor Project | 2025-26

**Tech Stack:** Python · Flask · SQLAlchemy · SQLite/MySQL · JWT · HTML5 · CSS3 · JavaScript

---

## 📁 Project Structure

```
cirs-project/
│
├── 🟢 START_WINDOWS.bat        ← Double-click to run on Windows
├── 🟢 START_MAC_LINUX.sh       ← Run on Mac/Linux
│
├── backend/
│   ├── app.py                  ← Python Flask API (main server)
│   ├── requirements.txt        ← Python packages needed
│   └── cirs.db                 ← SQLite database (auto-created on first run)
│
├── frontend/
│   ├── index.html              ← Main web page
│   ├── css/style.css           ← Design system
│   └── js/app.js               ← Frontend logic (connects to Flask API)
│
└── uploads/                    ← Uploaded complaint images (auto-created)
```

---

## 🚀 HOW TO RUN (Step by Step)

### Prerequisites
- **Python 3.8+** installed → [Download](https://python.org/downloads)
  - ⚠️ On Windows: check **"Add Python to PATH"** during installation!

---

### ▶️ Windows

1. Extract the ZIP/RAR folder
2. **Double-click** `START_WINDOWS.bat`
3. Wait for packages to install (first time only)
4. Browser opens at **http://localhost:5000**

---

### ▶️ Mac / Linux

1. Extract the folder
2. Open Terminal in the project folder
3. Run:
```bash
chmod +x START_MAC_LINUX.sh
./START_MAC_LINUX.sh
```
4. Open **http://localhost:5000** in your browser

---

### ▶️ Manual Start (Any OS)

```bash
# 1. Go to backend folder
cd backend

# 2. Install packages (only needed once)
pip install -r requirements.txt

# 3. Start the server
python app.py
```

Open http://localhost:5000 in your browser.

---

## 🔐 Login Credentials

| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@cdgi.edu.in | admin123 |

> The database starts **empty**. The admin account is the only pre-created user.
> Register new accounts using the **Create Account** button.

---

## 🗄️ Database (SQLite — Zero Config!)

The database file `backend/cirs.db` is **automatically created** when you first run the server. No setup needed!

### Tables Created Automatically:

| Table | Purpose |
|-------|---------|
| `users` | Stores all user accounts (name, email, hashed password, role) |
| `complaints` | All submitted tickets with status, category, images |
| `notifications` | System notifications per user |

### View Your Database (Optional)
Download **DB Browser for SQLite** (free): https://sqlitebrowser.org
Open `backend/cirs.db` to see all your data visually.

---

## ☁️ Switch to MySQL (For Cloud Deployment)

### Step 1: Install MySQL driver
```bash
pip install pymysql
```

### Step 2: Edit `backend/app.py` line ~25
Replace:
```python
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
```
With:
```python
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://USERNAME:PASSWORD@HOST/DBNAME"
```

**Examples:**
```python
# Local MySQL
"mysql+pymysql://root:yourpassword@localhost/cirs_db"

# InfinityFree (free hosting)
"mysql+pymysql://if0_12345678:pass@sql123.infinityfree.com/if0_12345678_cirs"

# Railway.app (free cloud)
"mysql+pymysql://root:pass@containers-us-west-1.railway.app:7777/railway"

# PlanetScale (free cloud MySQL)
"mysql+pymysql://user:pass@host/dbname?ssl_ca=/etc/ssl/certs/ca-certificates.crt"
```

### Step 3: Restart
```bash
python app.py
```
All tables create themselves automatically!

---

## 🌐 Deploy Online (Free Hosting Options)

### Option A: Railway.app (Easiest — Recommended)
1. Sign up at https://railway.app (free)
2. Install Railway CLI: `npm install -g @railway/cli`
3. In project folder:
```bash
railway login
railway init
railway up
```
4. Railway gives you a live URL automatically!

### Option B: Render.com (Free)
1. Push code to GitHub
2. Go to https://render.com
3. New → Web Service → connect your GitHub repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `python app.py`

### Option C: PythonAnywhere (Free)
1. Sign up at https://pythonanywhere.com
2. Upload your files via Files tab
3. Set up a Web app with Flask
4. Point it to your `backend/app.py`

---

## 🔑 API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | /api/register | Register new user | No |
| POST | /api/login | Login, get JWT token | No |
| GET | /api/me | Get current user | Yes |
| PUT | /api/profile | Update profile | Yes |
| GET | /api/complaints | Get complaints (filtered) | Yes |
| POST | /api/complaints | Submit new complaint | Yes |
| GET | /api/complaints/:id | Get single complaint | Yes |
| PUT | /api/complaints/:id | Update status/feedback | Yes |
| DELETE | /api/complaints/:id | Delete complaint | Yes (admin) |
| GET | /api/stats | Dashboard statistics | Yes |
| GET | /api/users | All users | Admin only |
| PUT | /api/users/:id/role | Change user role | Admin only |
| GET | /api/notifications | Get notifications | Yes |
| PUT | /api/notifications/read-all | Mark all read | Yes |

---

## 🔐 Security Features

- ✅ Passwords hashed with **bcrypt** (never stored plain)
- ✅ **JWT tokens** — 7-day expiry, signed with HMAC-SHA256
- ✅ **Role-Based Access Control** — Student / Coordinator / Admin
- ✅ **SQL Injection prevention** — SQLAlchemy ORM with parameterized queries
- ✅ **File upload validation** — whitelist of allowed extensions
- ✅ **CORS** configured for cross-origin requests

---

## 👨‍💻 Team

| Name | Roll No | Module |
|------|---------|--------|
| Aakash Thakur | 0832CS231003 | Reporting & Analytics |
| Abhay Pratap Singh | 0832CS231007 | Departmental Workflow |
| Avani Jaiswal | 0832CS231034 | Frontend Interface |
| Chhavi Sharma | 0832CS231052 | Backend Developer |

**Guide:** Prof. Radheshyam Acholiya (HOD-CSE)
**Institution:** Chameli Devi Group of Institutions, Indore (M.P.) 452020
**Session:** 2025-26
