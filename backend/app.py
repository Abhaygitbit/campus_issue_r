"""
╔══════════════════════════════════════════════════════════╗
║   Campus Issues Reporting System — Python Flask Backend  ║
║   CDGI Indore · 2025-26                                  ║
║   Tech Stack: Python + Flask + SQLite/MySQL + JWT        ║
╚══════════════════════════════════════════════════════════╝
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os, random, string
from urllib.parse import quote_plus

# ─────────────────────────────────────────────
#  APP CONFIGURATION
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Database: SQLite by default (zero config!)
# ── To use MySQL: change URI to mysql+pymysql://user:pass@host/dbname
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"]                 = "CIRS_CDGI_SECRET_2025_CHANGE_IN_PROD"
app.config["JWT_ACCESS_TOKEN_EXPIRES"]       = timedelta(days=7)
app.config["UPLOAD_FOLDER"]                  = os.path.join(BASE_DIR, "../uploads")
app.config["MAX_CONTENT_LENGTH"]             = 16 * 1024 * 1024  # 16 MB max upload

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "pdf"}

db  = SQLAlchemy(app)
jwt = JWTManager(app)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ─────────────────────────────────────────────
#  DATABASE MODELS
# ─────────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    role       = db.Column(db.String(30),  default="student")   # student/coordinator/admin
    dept       = db.Column(db.String(100), default="CSE")
    roll_no    = db.Column(db.String(50))
    phone      = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    complaints = db.relationship("Complaint", backref="reporter", lazy=True)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "role": self.role, "dept": self.dept, "roll_no": self.roll_no,
            "phone": self.phone,
            "created_at": self.created_at.strftime("%Y-%m-%d")
        }


class Complaint(db.Model):
    __tablename__ = "complaints"
    id          = db.Column(db.Integer, primary_key=True)
    ticket_id   = db.Column(db.String(20), unique=True, nullable=False)
    title       = db.Column(db.String(250), nullable=False)
    category    = db.Column(db.String(50),  nullable=False)
    description = db.Column(db.Text,        nullable=False)
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
        return {
            "id": self.id, "ticket_id": self.ticket_id,
            "title": self.title, "category": self.category,
            "description": self.description, "priority": self.priority,
            "status": self.status, "location": self.location,
            "image_path": self.image_path, "dept": self.dept,
            "assigned_to": self.assigned_to, "feedback": self.feedback,
            "user_id": self.user_id,
            "user_name": self.reporter.name if self.reporter else "",
            "user_email": self.reporter.email if self.reporter else "",
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

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
CAT_DEPT = {
    "hygiene": "Maintenance", "electrical": "Electrical",
    "transport": "Transport", "maintenance": "Maintenance",
    "safety": "Security", "admin": "Administration", "water": "Maintenance"
}

def gen_ticket(count):
    return f"TKT-{str(count + 1).zfill(4)}"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def push_notification(user_id, message):
    n = Notification(user_id=user_id, message=message)
    db.session.add(n)
    db.session.commit()

# ─────────────────────────────────────────────
#  SERVE FRONTEND
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")

# ─────────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    required = ["name", "email", "password"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Field '{f}' is required"}), 400

    if User.query.filter_by(email=data["email"].lower().strip()).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        name     = data["name"].strip(),
        email    = data["email"].lower().strip(),
        password = generate_password_hash(data["password"]),
        role     = data.get("role", "student"),
        dept     = data.get("dept", "CSE"),
        roll_no  = data.get("roll_no", ""),
        phone    = data.get("phone", "")
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"status": "success", "token": token, "user": user.to_dict()}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=data["email"].lower().strip()).first()
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"status": "success", "token": token, "user": user.to_dict()})


@app.route("/api/me", methods=["GET"])
@jwt_required()
def me():
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    return jsonify(user.to_dict())


@app.route("/api/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    data = request.get_json()
    if data.get("name"):    user.name  = data["name"]
    if data.get("phone"):   user.phone = data["phone"]
    if data.get("password"):
        user.password = generate_password_hash(data["password"])
    db.session.commit()
    return jsonify({"status": "success", "user": user.to_dict()})

# ─────────────────────────────────────────────
#  COMPLAINT ROUTES
# ─────────────────────────────────────────────
@app.route("/api/complaints", methods=["GET"])
@jwt_required()
def get_complaints():
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)

    q = Complaint.query
    if user.role not in ("admin", "coordinator"):
        q = q.filter_by(user_id=uid)

    # filters
    status   = request.args.get("status")
    category = request.args.get("category")
    search   = request.args.get("search")
    if status:   q = q.filter_by(status=status)
    if category: q = q.filter_by(category=category)
    if search:
        q = q.filter(
            db.or_(
                Complaint.title.ilike(f"%{search}%"),
                Complaint.ticket_id.ilike(f"%{search}%")
            )
        )

    complaints = q.order_by(Complaint.created_at.desc()).all()
    return jsonify({"status": "success", "data": [c.to_dict() for c in complaints],
                    "count": len(complaints)})


@app.route("/api/complaints", methods=["POST"])
@jwt_required()
def create_complaint():
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)

    title       = request.form.get("title", "").strip()
    category    = request.form.get("category", "")
    description = request.form.get("description", "").strip()
    priority    = request.form.get("priority", "medium")
    location    = request.form.get("location", "").strip()

    if not title or not category or not description:
        return jsonify({"error": "Title, category and description are required"}), 400

    count     = Complaint.query.count()
    ticket_id = gen_ticket(count)
    img_path  = None

    # Handle file upload
    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename = f"{ticket_id}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            img_path = f"/uploads/{filename}"

    complaint = Complaint(
        ticket_id   = ticket_id,
        title       = title,
        category    = category,
        description = description,
        priority    = priority,
        location    = location,
        dept        = CAT_DEPT.get(category, "General"),
        image_path  = img_path,
        user_id     = uid
    )
    db.session.add(complaint)

    # Notify all admins
    admins = User.query.filter_by(role="admin").all()
    for admin in admins:
        push_notification(admin.id, f"New complaint {ticket_id}: {title} — from {user.name}")

    db.session.commit()
    return jsonify({
        "status": "success",
        "message": f"Complaint {ticket_id} submitted successfully!",
        "complaint": complaint.to_dict()
    }), 201


@app.route("/api/complaints/<ticket_id>", methods=["GET"])
@jwt_required()
def get_complaint(ticket_id):
    c = Complaint.query.filter_by(ticket_id=ticket_id).first_or_404()
    return jsonify(c.to_dict())


@app.route("/api/complaints/<ticket_id>", methods=["PUT"])
@jwt_required()
def update_complaint(ticket_id):
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    c    = Complaint.query.filter_by(ticket_id=ticket_id).first_or_404()
    data = request.get_json()

    # Only admin/coordinator can update status
    if user.role in ("admin", "coordinator"):
        if "status"      in data: c.status      = data["status"]
        if "assigned_to" in data: c.assigned_to = data["assigned_to"]
        c.updated_at = datetime.utcnow()
        db.session.commit()
        # Notify reporter
        push_notification(c.user_id, f"Your complaint {ticket_id} status changed to: {c.status}")
        return jsonify({"status": "success", "complaint": c.to_dict()})

    # Feedback — only reporter, only when resolved
    if "feedback" in data and c.user_id == uid and c.status == "resolved":
        c.feedback = int(data["feedback"])
        db.session.commit()
        return jsonify({"status": "success", "message": "Feedback submitted!"})

    return jsonify({"error": "Unauthorized"}), 403


@app.route("/api/complaints/<ticket_id>", methods=["DELETE"])
@jwt_required()
def delete_complaint(ticket_id):
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    c    = Complaint.query.filter_by(ticket_id=ticket_id).first_or_404()

    if user.role != "admin" and c.user_id != uid:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(c)
    db.session.commit()
    return jsonify({"status": "success", "message": f"{ticket_id} deleted"})

# ─────────────────────────────────────────────
#  STATS (Dashboard data)
# ─────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
@jwt_required()
def get_stats():
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)

    if user.role in ("admin", "coordinator"):
        base = Complaint.query
    else:
        base = Complaint.query.filter_by(user_id=uid)

    total      = base.count()
    new_c      = base.filter_by(status="new").count()
    in_prog    = Complaint.query.filter_by(status="in-progress").count() if user.role in ("admin","coordinator") else base.filter_by(status="in-progress").count()
    resolved   = base.filter_by(status="resolved").count()
    total_users = User.query.count() if user.role == "admin" else None

    # Category breakdown
    cats = {}
    for c in (Complaint.query.all() if user.role in ("admin","coordinator") else base.all()):
        cats[c.category] = cats.get(c.category, 0) + 1

    return jsonify({
        "total": total, "new": new_c, "in_progress": in_prog,
        "resolved": resolved, "categories": cats,
        "total_users": total_users,
        "resolution_rate": round((resolved / total * 100) if total else 0, 1)
    })

# ─────────────────────────────────────────────
#  USERS (Admin only)
# ─────────────────────────────────────────────
@app.route("/api/users", methods=["GET"])
@jwt_required()
def get_users():
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    if user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"status": "success", "data": [u.to_dict() for u in users]})


@app.route("/api/users/<int:user_id>/role", methods=["PUT"])
@jwt_required()
def update_user_role(user_id):
    uid  = int(get_jwt_identity())
    me   = User.query.get_or_404(uid)
    if me.role != "admin":
        return jsonify({"error": "Admin access required"}), 403
    target = User.query.get_or_404(user_id)
    data   = request.get_json()
    if "role" in data:
        target.role = data["role"]
        db.session.commit()
    return jsonify({"status": "success", "user": target.to_dict()})

# ─────────────────────────────────────────────
#  NOTIFICATIONS
# ─────────────────────────────────────────────
@app.route("/api/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    uid   = int(get_jwt_identity())
    notifs = Notification.query.filter_by(user_id=uid)\
                .order_by(Notification.created_at.desc()).limit(20).all()
    unread = Notification.query.filter_by(user_id=uid, is_read=False).count()
    return jsonify({"data": [n.to_dict() for n in notifs], "unread": unread})


@app.route("/api/notifications/read-all", methods=["PUT"])
@jwt_required()
def mark_all_read():
    uid = int(get_jwt_identity())
    Notification.query.filter_by(user_id=uid, is_read=False)\
        .update({"is_read": True})
    db.session.commit()
    return jsonify({"status": "success"})

# ─────────────────────────────────────────────
#  FILE UPLOADS
# ─────────────────────────────────────────────
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ─────────────────────────────────────────────
#  DB INIT
# ─────────────────────────────────────────────
with app.app_context():
    db.create_all()
    # Create default admin if none exists
    if not User.query.filter_by(role="admin").first():
        admin = User(
            name     = "Admin CDGI",
            email    = "admin@cdgi.edu.in",
            password = generate_password_hash("admin123"),
            role     = "admin",
            dept     = "CSE",
            roll_no  = "ADMIN001"
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created: admin@cdgi.edu.in / admin123")

if __name__ == "__main__":
    print("━" * 55)
    print("  🏛️  Campus Issues Reporting System")
    print("  📍 CDGI Indore | Python + Flask + SQLite")
    print("  🌐 Open: http://localhost:5000")
    print("━" * 55)
    app.run(debug=True, port=5000, host="0.0.0.0")
