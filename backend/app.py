"""
╔══════════════════════════════════════════════════════════════╗
║  CIRS — Campus Issues Reporting System  v3                   ║
║  CDGI Indore · 2025-26                                        ║
║  Changes: Staff limited menu, Faculty sees all, Admin deletes ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, re, smtplib, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Database ──────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_NAME     = os.getenv("DB_NAME", "postgres")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_PORT     = os.getenv("DB_PORT", "5432")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"sslmode": "require"},
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"]           = os.getenv("JWT_SECRET", "CIRS_CDGI_V3_SECRET_2025")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
app.config["UPLOAD_FOLDER"]            = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"]       = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "pdf"}

db  = SQLAlchemy(app)
jwt = JWTManager(app)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Email ─────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASS     = os.getenv("SMTP_PASS", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_ENABLED = bool(SMTP_USER and SMTP_PASS)

# ── Role constants ────────────────────────────────
# Roles that can VIEW all complaints and mark resolved:
CAN_VIEW_ALL   = ("admin", "coordinator", "faculty")
# Roles that can CHANGE status / priority:
CAN_MANAGE     = ("admin", "coordinator", "faculty")
# Only admin can delete users:
ADMIN_ONLY     = ("admin",)

# ═══════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════
class User(db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    role       = db.Column(db.String(30),  default="student")
    dept       = db.Column(db.String(100), default="CSE")
    roll_no    = db.Column(db.String(50))
    phone      = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    complaints = db.relationship("Complaint", backref="reporter", lazy=True,
                                  foreign_keys="Complaint.user_id")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "role": self.role, "dept": self.dept,
            "roll_no": self.roll_no or "",
            "phone":   self.phone   or "",
            "created_at": self.created_at.strftime("%Y-%m-%d")
        }


class Complaint(db.Model):
    __tablename__ = "complaints"
    id          = db.Column(db.Integer, primary_key=True)
    ticket_id   = db.Column(db.String(20),  unique=True, nullable=False)
    title       = db.Column(db.String(250), nullable=False)
    category    = db.Column(db.String(50),  nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority    = db.Column(db.String(20),  default="medium")
    status      = db.Column(db.String(30),  default="new")
    location    = db.Column(db.String(200))
    image_path  = db.Column(db.String(300))
    dept        = db.Column(db.String(100))
    assigned_to = db.Column(db.String(150))
    feedback    = db.Column(db.Integer)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        base = os.getenv("APP_URL", "http://localhost:5000")
        img  = f"{base}{self.image_path}" if self.image_path else None
        return {
            "id": self.id, "ticket_id": self.ticket_id,
            "title": self.title, "category": self.category,
            "description": self.description, "priority": self.priority,
            "status": self.status, "location": self.location or "",
            "image_path": img,
            "dept": self.dept or "",
            "assigned_to": self.assigned_to or "",
            "feedback": self.feedback,
            "user_id":    self.user_id,
            "user_name":  self.reporter.name  if self.reporter else "",
            "user_email": self.reporter.email if self.reporter else "",
            "user_dept":  self.reporter.dept  if self.reporter else "",
            "user_roll":  self.reporter.roll_no if self.reporter else "",
            "user_phone": self.reporter.phone  if self.reporter else "",
            "created_at": self.created_at.strftime("%Y-%m-%d"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d") if self.updated_at else ""
        }


class Notification(db.Model):
    __tablename__ = "notifications"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "message": self.message, "is_read": self.is_read,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
        }

# ═══════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════
CAT_DEPT = {
    "hygiene": "Maintenance", "electrical": "Electrical",
    "transport": "Transport",  "maintenance": "Maintenance",
    "safety": "Security",      "admin": "Administration",
    "water": "Maintenance"
}
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES   = {"new", "in-progress", "resolved"}

def gen_ticket():
    count = Complaint.query.count()
    return f"TKT-{str(count + 1).zfill(4)}"

def allowed_file(f):
    return "." in f and f.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_phone(p):
    return bool(re.fullmatch(r"\d{10}", p)) if p else True

def push_notification(user_id, message):
    try:
        n = Notification(user_id=user_id, message=message)
        db.session.add(n)
        db.session.commit()
    except Exception as e:
        print(f"[NOTIF ERR] {e}")

# ── Email ─────────────────────────────────────────
def _send_worker(to_email, subject, html):
    if not EMAIL_ENABLED:
        print(f"[EMAIL SKIP] {to_email}: {subject}")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"CDGI CIRS <{EMAIL_FROM}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.ehlo(); s.starttls(); s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(EMAIL_FROM, to_email, msg.as_string())
        print(f"[EMAIL OK] {to_email}")
    except Exception as e:
        print(f"[EMAIL ERR] {e}")

def send_email(to, subject, html):
    threading.Thread(target=_send_worker, args=(to, subject, html), daemon=True).start()

def email_submitted(email, name, tid, title, desc, cat):
    send_email(email, f"✅ Complaint {tid} Received | CDGI CIRS", f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
      <div style="background:linear-gradient(135deg,#1d4ed8,#0369a1);padding:24px 32px;border-radius:12px 12px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;">🏛️ CDGI Campus Issues Portal</h1>
        <p style="color:#bfdbfe;margin:4px 0 0;font-size:12px;">Chameli Devi Group of Institutions, Indore</p>
      </div>
      <div style="padding:24px 32px;background:#fff;border:1px solid #e2e8f0;border-top:none;">
        <p>Dear <strong>{name}</strong>, your complaint has been registered.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">
          <tr style="background:#eff6ff;"><td style="padding:8px 12px;font-weight:600;">Ticket ID</td><td style="padding:8px 12px;color:#1d4ed8;font-weight:700;">{tid}</td></tr>
          <tr><td style="padding:8px 12px;font-weight:600;">Title</td><td style="padding:8px 12px;">{title}</td></tr>
          <tr style="background:#eff6ff;"><td style="padding:8px 12px;font-weight:600;">Category</td><td style="padding:8px 12px;">{cat.capitalize()}</td></tr>
          <tr><td style="padding:8px 12px;font-weight:600;">Status</td><td style="padding:8px 12px;"><span style="background:#dbeafe;color:#1d4ed8;padding:2px 10px;border-radius:20px;font-size:12px;">🆕 New</span></td></tr>
        </table>
        <p style="font-size:13px;color:#64748b;">Keep your Ticket ID <strong>{tid}</strong> for tracking purposes.</p>
      </div>
      <div style="background:#f8fafc;padding:12px 32px;border-radius:0 0 12px 12px;text-align:center;">
        <p style="color:#94a3b8;font-size:11px;margin:0;">CDGI CIRS · Indore M.P. 452020</p>
      </div>
    </div>""")

def email_status(email, name, tid, title, status, assigned=""):
    colors = {"new":("#dbeafe","#1d4ed8","🆕 New"),"in-progress":("#fef3c7","#92400e","⏳ In Progress"),"resolved":("#dcfce7","#166534","✅ Resolved")}
    bg,fg,lbl = colors.get(status,("#f1f5f9","#334155",status))
    send_email(email, f"📢 {tid} Status Update | CDGI CIRS", f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
      <div style="background:linear-gradient(135deg,#1d4ed8,#0369a1);padding:24px 32px;border-radius:12px 12px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;">🏛️ CDGI Campus Issues Portal</h1>
      </div>
      <div style="padding:24px 32px;background:#fff;border:1px solid #e2e8f0;border-top:none;">
        <p>Dear <strong>{name}</strong>, your complaint status has been updated.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">
          <tr style="background:#eff6ff;"><td style="padding:8px 12px;font-weight:600;">Ticket ID</td><td style="padding:8px 12px;color:#1d4ed8;font-weight:700;">{tid}</td></tr>
          <tr><td style="padding:8px 12px;font-weight:600;">Title</td><td style="padding:8px 12px;">{title}</td></tr>
          <tr style="background:#eff6ff;"><td style="padding:8px 12px;font-weight:600;">Status</td><td style="padding:8px 12px;"><span style="background:{bg};color:{fg};padding:2px 10px;border-radius:20px;font-size:12px;">{lbl}</span></td></tr>
          {f'<tr><td style="padding:8px 12px;font-weight:600;">Assigned To</td><td style="padding:8px 12px;">{assigned}</td></tr>' if assigned else ""}
        </table>
        {'<p style="background:#dcfce7;color:#166534;padding:12px;border-radius:8px;font-size:13px;">🎉 Your issue has been resolved! Please log in to rate the service.</p>' if status=="resolved" else ""}
      </div>
    </div>""")

# ═══════════════════════════════════════════════════
#  SERVE FRONTEND
# ═══════════════════════════════════════════════════
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ═══════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    for f in ["name","email","password"]:
        if not data.get(f,"").strip():
            return jsonify({"error": f"Field '{f}' is required"}), 400

    phone = data.get("phone","").strip()
    if phone and not validate_phone(phone):
        return jsonify({"error": "Phone must be exactly 10 digits"}), 400
    if len(data["password"]) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    email = data["email"].lower().strip()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        name=data["name"].strip(), email=email,
        password=generate_password_hash(data["password"]),
        role=data.get("role","student"),
        dept=data.get("dept","CSE"),
        roll_no=data.get("roll_no",""), phone=phone
    )
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({"status":"success","token":token,"user":user.to_dict()}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400
    user = User.query.filter_by(email=data["email"].lower().strip()).first()
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401
    token = create_access_token(identity=str(user.id))
    return jsonify({"status":"success","token":token,"user":user.to_dict()})


@app.route("/api/me", methods=["GET"])
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user: return jsonify({"error":"Not found"}), 404
    return jsonify(user.to_dict())


@app.route("/api/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user: return jsonify({"error":"Not found"}), 404
    data = request.get_json() or {}
    if data.get("name"):  user.name = data["name"].strip()
    phone = data.get("phone","").strip()
    if phone:
        if not validate_phone(phone):
            return jsonify({"error":"Phone must be exactly 10 digits"}), 400
        user.phone = phone
    if data.get("password"):
        if len(data["password"]) < 6:
            return jsonify({"error":"Password must be at least 6 characters"}), 400
        user.password = generate_password_hash(data["password"])
    db.session.commit()
    return jsonify({"status":"success","user":user.to_dict()})

# ═══════════════════════════════════════════════════
#  COMPLAINTS
# ═══════════════════════════════════════════════════
@app.route("/api/complaints", methods=["GET"])
@jwt_required()
def get_complaints():
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user: return jsonify({"error":"Not found"}), 404

    q = Complaint.query
    # Admin, coordinator, faculty see ALL complaints
    # Staff and students see only their own
    if user.role not in CAN_VIEW_ALL:
        q = q.filter_by(user_id=uid)

    status   = request.args.get("status")
    category = request.args.get("category")
    search   = request.args.get("search")
    if status:   q = q.filter_by(status=status)
    if category: q = q.filter_by(category=category)
    if search:
        q = q.filter(db.or_(
            Complaint.title.ilike(f"%{search}%"),
            Complaint.ticket_id.ilike(f"%{search}%")
        ))

    complaints = q.order_by(Complaint.created_at.desc()).all()
    return jsonify({"status":"success","data":[c.to_dict() for c in complaints],"count":len(complaints)})


@app.route("/api/complaints", methods=["POST"])
@jwt_required()
def create_complaint():
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user: return jsonify({"error":"Not found"}), 404

    title       = request.form.get("title","").strip()
    category    = request.form.get("category","").strip()
    description = request.form.get("description","").strip()
    location    = request.form.get("location","").strip()

    if not title or not category or not description:
        return jsonify({"error":"Title, category and description are required"}), 400
    if category not in CAT_DEPT:
        return jsonify({"error":"Invalid category"}), 400

    # Only admin/coordinator can set priority
    if user.role in ("admin","coordinator"):
        priority = request.form.get("priority","medium")
        if priority not in VALID_PRIORITIES: priority = "medium"
    else:
        priority = "medium"

    img_path = None
    if "image" in request.files:
        f = request.files["image"]
        if f and f.filename and allowed_file(f.filename):
            fname = f"{gen_ticket()}_{secure_filename(f.filename)}"
            f.save(os.path.join(app.config["UPLOAD_FOLDER"], fname))
            img_path = f"/uploads/{fname}"

    ticket_id = gen_ticket()
    c = Complaint(
        ticket_id=ticket_id, title=title, category=category,
        description=description, priority=priority, location=location,
        dept=CAT_DEPT.get(category,"General"), image_path=img_path, user_id=uid
    )
    db.session.add(c)

    # Notify all admins + coordinators + faculty
    for u in User.query.filter(User.role.in_(["admin","coordinator","faculty"])).all():
        push_notification(u.id, f"New complaint {ticket_id}: {title} — by {user.name}")

    db.session.commit()
    email_submitted(user.email, user.name, ticket_id, title, description, category)

    return jsonify({"status":"success","message":f"Complaint {ticket_id} submitted!","complaint":c.to_dict()}), 201


@app.route("/api/complaints/<ticket_id>", methods=["GET"])
@jwt_required()
def get_complaint(ticket_id):
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    c    = Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}), 404
    if user.role not in CAN_VIEW_ALL and c.user_id != uid:
        return jsonify({"error":"Unauthorized"}), 403
    return jsonify(c.to_dict())


@app.route("/api/complaints/<ticket_id>", methods=["PUT"])
@jwt_required()
def update_complaint(ticket_id):
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    c    = Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}), 404
    data = request.get_json() or {}

    # Admin, Coordinator, Faculty can manage complaints
    if user.role in CAN_MANAGE:
        old_status = c.status
        if "status" in data:
            if data["status"] not in VALID_STATUSES:
                return jsonify({"error":"Invalid status"}), 400
            c.status = data["status"]
        if "priority" in data and user.role in ("admin","coordinator"):
            if data["priority"] not in VALID_PRIORITIES:
                return jsonify({"error":"Invalid priority"}), 400
            c.priority = data["priority"]
        if "assigned_to" in data:
            c.assigned_to = data["assigned_to"]
        c.updated_at = datetime.utcnow()
        db.session.commit()
        reporter = db.session.get(User, c.user_id)
        push_notification(c.user_id, f"Complaint {ticket_id} updated to: {c.status}")
        if reporter and c.status != old_status:
            email_status(reporter.email, reporter.name, ticket_id, c.title, c.status, c.assigned_to or "")
        return jsonify({"status":"success","complaint":c.to_dict()})

    # Feedback — reporter only, resolved only
    if "feedback" in data and c.user_id == uid and c.status == "resolved":
        rating = int(data["feedback"])
        if not 1 <= rating <= 5:
            return jsonify({"error":"Rating 1-5 only"}), 400
        c.feedback = rating
        db.session.commit()
        return jsonify({"status":"success","message":"Feedback submitted!"})

    return jsonify({"error":"Unauthorized"}), 403


@app.route("/api/complaints/<ticket_id>", methods=["DELETE"])
@jwt_required()
def delete_complaint(ticket_id):
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    c    = Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}), 404
    if user.role != "admin" and c.user_id != uid:
        return jsonify({"error":"Unauthorized"}), 403
    if c.image_path:
        try:
            fname = c.image_path.split("/uploads/")[-1]
            fpath = os.path.join(app.config["UPLOAD_FOLDER"], fname)
            if os.path.exists(fpath): os.remove(fpath)
        except: pass
    db.session.delete(c)
    db.session.commit()
    return jsonify({"status":"success","message":f"{ticket_id} deleted"})

# ═══════════════════════════════════════════════════
#  STATS
# ═══════════════════════════════════════════════════
@app.route("/api/stats", methods=["GET"])
@jwt_required()
def get_stats():
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user: return jsonify({"error":"Not found"}), 404

    if user.role in CAN_VIEW_ALL:
        base = Complaint.query
    else:
        base = Complaint.query.filter_by(user_id=uid)

    total    = base.count()
    new_c    = base.filter_by(status="new").count()
    in_prog  = base.filter_by(status="in-progress").count()
    resolved = base.filter_by(status="resolved").count()
    cats = {}
    for c in base.all():
        cats[c.category] = cats.get(c.category, 0) + 1

    return jsonify({
        "total":total, "new":new_c, "in_progress":in_prog, "resolved":resolved,
        "categories":cats,
        "total_users": User.query.count() if user.role=="admin" else None,
        "resolution_rate": round((resolved/total*100) if total else 0, 1)
    })

# ═══════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════
@app.route("/api/users", methods=["GET"])
@jwt_required()
def get_users():
    uid  = int(get_jwt_identity())
    user = db.session.get(User, uid)
    # Admin and coordinator can view users
    if not user or user.role not in ("admin","coordinator"):
        return jsonify({"error":"Access denied"}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"status":"success","data":[u.to_dict() for u in users]})


@app.route("/api/users/<int:user_id>/role", methods=["PUT"])
@jwt_required()
def update_role(user_id):
    uid    = int(get_jwt_identity())
    caller = db.session.get(User, uid)
    if not caller or caller.role != "admin":
        return jsonify({"error":"Admin only"}), 403
    target = db.session.get(User, user_id)
    if not target: return jsonify({"error":"User not found"}), 404
    data = request.get_json() or {}
    valid = {"student","faculty","staff","coordinator","admin"}
    if data.get("role") in valid:
        target.role = data["role"]
        db.session.commit()
    return jsonify({"status":"success","user":target.to_dict()})


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    """Only admin can delete users."""
    uid    = int(get_jwt_identity())
    caller = db.session.get(User, uid)
    if not caller or caller.role != "admin":
        return jsonify({"error":"Only admin can delete users"}), 403
    if caller.id == user_id:
        return jsonify({"error":"Cannot delete your own account"}), 400
    target = db.session.get(User, user_id)
    if not target: return jsonify({"error":"User not found"}), 404
    db.session.delete(target)
    db.session.commit()
    return jsonify({"status":"success","message":f"User {target.name} deleted"})

# ═══════════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════════
@app.route("/api/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    uid    = int(get_jwt_identity())
    notifs = Notification.query.filter_by(user_id=uid)\
                 .order_by(Notification.created_at.desc()).limit(20).all()
    unread = Notification.query.filter_by(user_id=uid, is_read=False).count()
    return jsonify({"data":[n.to_dict() for n in notifs],"unread":unread})


@app.route("/api/notifications/read-all", methods=["PUT"])
@jwt_required()
def mark_all_read():
    uid = int(get_jwt_identity())
    Notification.query.filter_by(user_id=uid, is_read=False).update({"is_read":True})
    db.session.commit()
    return jsonify({"status":"success"})

# ═══════════════════════════════════════════════════
#  DB INIT
# ═══════════════════════════════════════════════════
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables ready")
        if not User.query.filter_by(role="admin").first():
            admin = User(
                name="Admin CDGI", email="admin@cdgi.edu.in",
                password=generate_password_hash("admin123"),
                role="admin", dept="CSE", roll_no="ADMIN001", phone="0000000000"
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin created: admin@cdgi.edu.in / admin123")
    except Exception as e:
        print(f"❌ DB Error: {e}")

if __name__ == "__main__":
    print("━"*50)
    print("  🏛️  CIRS v3 | CDGI Indore")
    print("  🌐 http://localhost:5000")
    print(f"  📧 Email: {'✅' if EMAIL_ENABLED else '⚠️ Not configured'}")
    print("━"*50)
    app.run(debug=True, port=5000, host="0.0.0.0")
