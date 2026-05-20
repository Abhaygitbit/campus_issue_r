# 🏛️ Campus Issues Reporting System (CIRS)
### CDGI Indore — Minor Project | 2025-26

**Tech Stack:** Python · Flask · SQLAlchemy · SQLite/MySQL · JWT · HTML5 · CSS3 · JavaScript

---

## 📁 Project Structure

```
cirs-project
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

### ▶️ Manual Start (Any OS)

```bash
# 1. Go to backend folder
cd backend

# 2. Install packages (only needed once)




> The database starts **empty**. The admin account is the only pre-created user.
> Register new accounts using the **Create Account** button.

### 🌐 Frontend Backend URL (Production)
- Local development uses `http://localhost:5002`.
- Production uses the same origin automatically.
- If frontend and backend are on different domains, set this before loading `js/app.js`:
```html
<script>window.CIRS_BACKEND_URL = "https://your-backend-domain.com";</script>
```

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

use supabase

### Step 3: Restart
```bash
python app.py
```
All tables create themselves automatically!

---

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
