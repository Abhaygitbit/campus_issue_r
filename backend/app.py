"""
CIRS v5 — Staff Assignment Workflow + Multi Image Support
CDGI Indore 2025-26
"""
import os, re, base64, secrets, smtplib
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory, has_request_context
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_API_OK = True
except ImportError:
    GMAIL_API_OK = False

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")
TOKEN_FILE = os.path.join(BASE_DIR, "gmail_token.json")
APP_URL    = os.getenv("APP_URL", "http://localhost:5002")
RENDER_ENV = os.getenv("RENDER", "").lower() == "true" or bool(os.getenv("RENDER_EXTERNAL_URL"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()
if RENDER_EXTERNAL_URL:
    APP_URL = RENDER_EXTERNAL_URL.rstrip("/")

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

DB_HOST=os.getenv("DB_HOST","localhost"); DB_NAME=os.getenv("DB_NAME","postgres")
DB_USER=os.getenv("DB_USER","postgres"); DB_PASSWORD=os.getenv("DB_PASSWORD","password")
DB_PORT=os.getenv("DB_PORT","5432")
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
if USE_SQLITE:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'cirs.db')}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args":{"sslmode":"require"},"pool_pre_ping":True,"pool_recycle":300}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET","CIRS_CDGI_V5_SECRET")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 32*1024*1024

ALLOWED_EXT = {"png","jpg","jpeg","webp","gif","mp4","pdf"}
IMAGE_EXT = {"png","jpg","jpeg","webp"}
SMTP_HOST=os.getenv("SMTP_HOST","smtp.gmail.com").strip(); SMTP_PORT=int(os.getenv("SMTP_PORT","587"))
SMTP_USER=os.getenv("SMTP_USER","").strip(); SMTP_PASS=os.getenv("SMTP_PASS","").replace(" ","").strip()
EMAIL_FROM=os.getenv("EMAIL_FROM",SMTP_USER).strip() or SMTP_USER; SMTP_OK=bool(SMTP_USER and SMTP_PASS)
EMAIL_VERIFY_ENABLED=os.getenv("EMAIL_VERIFY_ENABLED","false").lower()=="true"
DEFAULT_SEED_PASSWORD=os.getenv("SEED_DEFAULT_PASSWORD","Cirs@123")
SEED_DEFAULT_USERS=os.getenv("SEED_DEFAULT_USERS","true").lower()=="true"
SEED_RESET_PASSWORDS=os.getenv("SEED_RESET_PASSWORDS","true" if USE_SQLITE else "false").lower()=="true"
AUTO_VERIFY_USERS=os.getenv("AUTO_VERIFY_USERS","true").lower()=="true"
MAIL_MODE=os.getenv("MAIL_MODE","smtp" if RENDER_ENV else "auto").lower().strip()
MANAGE_ROLES={"admin","coordinator"}
ASSIGN_ROLES={"service_unit_manager"}
PHOTO_ALL_ROLES={"admin","coordinator"}
REPORTER_ROLES={"student","faculty"}

os.makedirs(UPLOAD_DIR,exist_ok=True)
db=SQLAlchemy(app)
jwt=JWTManager(app)

def ensure_db_schema():
    """Ensure database schema is up to date"""
    with app.app_context():
        try:
            db.create_all()
            # Keep legacy databases aligned with the current ORM model.
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if not inspector.has_table("complaints"):
                return

            cols = {c["name"] for c in inspector.get_columns("complaints")}
            stmts = []
            if "service_unit_id" not in cols:
                stmts.append("ALTER TABLE complaints ADD COLUMN service_unit_id INTEGER")
            if "is_escalated" not in cols:
                stmts.append("ALTER TABLE complaints ADD COLUMN is_escalated BOOLEAN DEFAULT FALSE")
            if "escalated_at" not in cols:
                stmts.append("ALTER TABLE complaints ADD COLUMN escalated_at TIMESTAMP")
            if "assigned_at" not in cols:
                stmts.append("ALTER TABLE complaints ADD COLUMN assigned_at TIMESTAMP")
            if "assigned_by_manager_id" not in cols:
                stmts.append("ALTER TABLE complaints ADD COLUMN assigned_by_manager_id INTEGER")

            if stmts:
                with db.engine.begin() as conn:
                    for stmt in stmts:
                        conn.execute(text(stmt))
        except Exception as e:
            print(f"Database schema check: {e}")

ensure_db_schema()

class User(db.Model):
    __tablename__="users"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(150),nullable=False)
    email=db.Column(db.String(150),unique=True,nullable=False)
    password=db.Column(db.String(255),nullable=False)
    role=db.Column(db.String(30),default="student")
    dept=db.Column(db.String(100),default="CSE")
    roll_no=db.Column(db.String(50))
    phone=db.Column(db.String(20))
    is_verified=db.Column(db.Boolean,default=False)
    verify_token=db.Column(db.String(100))
    verify_expires=db.Column(db.DateTime)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    service_unit_id=db.Column(db.Integer)
    academic_department=db.Column(db.String(100))
    complaints=db.relationship("Complaint",backref="reporter",lazy=True,foreign_keys="Complaint.user_id")
    assigned_complaints=db.relationship("Complaint",backref="assigned_staff",lazy=True,foreign_keys="Complaint.assigned_staff_id")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"email":self.email,"role":self.role,"dept":self.dept,
                "roll_no":self.roll_no or "","phone":self.phone or "","is_verified":self.is_verified,
                "service_unit_id":self.service_unit_id,"academic_department":self.academic_department or "",
                "created_at":self.created_at.strftime("%Y-%m-%d") if self.created_at else ""}

class Complaint(db.Model):
    __tablename__="complaints"
    id=db.Column(db.Integer,primary_key=True)
    ticket_id=db.Column(db.String(20),unique=True,nullable=False)
    title=db.Column(db.String(250),nullable=False)
    category=db.Column(db.String(50),nullable=False)
    description=db.Column(db.Text,nullable=False)
    priority=db.Column(db.String(20),default="medium")
    status=db.Column(db.String(30),default="routed")
    location=db.Column(db.String(200))
    image_before=db.Column(db.String(300))
    image_after=db.Column(db.String(300))
    dept=db.Column(db.String(100))
    assigned_to=db.Column(db.String(150))
    assigned_staff_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=True)
    assigned_by_manager_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=True)
    assigned_at=db.Column(db.DateTime,nullable=True)
    resolved_by=db.Column(db.String(150))
    feedback=db.Column(db.Integer)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    service_unit_id=db.Column(db.Integer,db.ForeignKey("service_units.id"),nullable=True)
    is_escalated=db.Column(db.Boolean,default=False)
    escalated_at=db.Column(db.DateTime,nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    assigned_by_manager=db.relationship("User",foreign_keys=[assigned_by_manager_id])
    service_unit=db.relationship("ServiceUnit",backref=db.backref("complaints",lazy="dynamic"))

    def normalize_status(self):
        self.status = normalize_status_value(self.status)

    def _can_view_student_images(self, viewer):
        if not viewer:
            return False
        return can_access_complaint(viewer, self)

    def _can_view_resolution_images(self, viewer):
        if not viewer:
            return False
        return can_access_complaint(viewer, self)

    def to_dict(self, viewer=None):
        self.normalize_status()
        can_view_student_images = self._can_view_student_images(viewer)
        can_view_resolution_images = self._can_view_resolution_images(viewer)
        issue_images = [img.to_dict() for img in self.issue_images.order_by(IssueImage.created_at.asc()).all()] if can_view_student_images else []
        resolution_images = [img.to_dict() for img in self.resolution_images.order_by(ResolutionImage.created_at.asc()).all()] if can_view_resolution_images else []
        if self.image_before and can_view_student_images and not issue_images:
            issue_images.append({"id": f"legacy_before_{self.id}", "image_url": media_url(self.image_before), "uploaded_by": "student", "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""})
        if self.image_after and can_view_resolution_images and not resolution_images:
            resolution_images.append({"id": f"legacy_after_{self.id}", "image_url": media_url(self.image_after), "uploaded_by": self.resolved_by or "staff", "created_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else ""})
        reporter_department = ""
        if self.reporter:
            reporter_department = self.reporter.academic_department or self.reporter.dept or ""
        return {
            "id":self.id,"ticket_id":self.ticket_id,"title":self.title,"category":self.category,
            "description":self.description,"status":self.status,
            "location":self.location or "",
            "image_before": issue_images[0]["image_url"] if issue_images else None,
            "image_after": resolution_images[0]["image_url"] if resolution_images else None,
            "issue_images": issue_images,
            "resolution_images": resolution_images,
            "dept":self.dept or "",
            "assigned_to":self.assigned_to or "",
            "assigned_staff_id": self.assigned_staff_id,
            "assigned_staff_name": self.assigned_staff.name if self.assigned_staff else (self.assigned_to or ""),
            "resolved_by":self.resolved_by or "","feedback":self.feedback,
            "user_id":self.user_id,
            "user_name":self.reporter.name if self.reporter else "",
            "user_email":self.reporter.email if self.reporter else "",
            "user_dept":self.reporter.dept if self.reporter else "",
            "reporter_academic_department": reporter_department,
            "user_roll":self.reporter.roll_no if self.reporter else "",
            "user_phone":self.reporter.phone if self.reporter else "",
            "service_unit_id":self.service_unit_id,
            "service_unit_name": self.service_unit.name if self.service_unit else "",
            "assigned_by_manager_id": self.assigned_by_manager_id,
            "assigned_manager_name": self.assigned_by_manager.name if self.assigned_by_manager else (self.service_unit.manager.name if self.service_unit and self.service_unit.manager else ""),
            "is_escalated":self.is_escalated,
            "escalated_at":self.escalated_at.strftime("%Y-%m-%d %H:%M") if self.escalated_at else None,
            "can_view_student_photo": can_view_student_images,
            "created_at":self.created_at.strftime("%Y-%m-%d"),
            "updated_at":self.updated_at.strftime("%Y-%m-%d") if self.updated_at else ""
        }

class IssueImage(db.Model):
    __tablename__="issue_images"
    id=db.Column(db.Integer,primary_key=True)
    complaint_id=db.Column(db.Integer,db.ForeignKey("complaints.id"),nullable=False,index=True)
    image_path=db.Column(db.String(300),nullable=False)
    uploaded_by=db.Column(db.String(50),default="student")
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    complaint=db.relationship("Complaint",backref=db.backref("issue_images",lazy="dynamic",cascade="all, delete-orphan"))
    def to_dict(self):
        return {"id": self.id, "image_url": media_url(self.image_path), "uploaded_by": self.uploaded_by, "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""}

class ResolutionImage(db.Model):
    __tablename__="resolution_images"
    id=db.Column(db.Integer,primary_key=True)
    complaint_id=db.Column(db.Integer,db.ForeignKey("complaints.id"),nullable=False,index=True)
    image_path=db.Column(db.String(300),nullable=False)
    uploaded_by_staff_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    complaint=db.relationship("Complaint",backref=db.backref("resolution_images",lazy="dynamic",cascade="all, delete-orphan"))
    staff=db.relationship("User")
    def to_dict(self):
        return {"id": self.id, "image_url": media_url(self.image_path), "uploaded_by": self.staff.name if self.staff else "staff", "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""}

class Notification(db.Model):
    __tablename__="notifications"
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    message=db.Column(db.Text,nullable=False)
    is_read=db.Column(db.Boolean,default=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    def to_dict(self):
        return {"id":self.id,"message":self.message,"is_read":self.is_read,"created_at":self.created_at.strftime("%Y-%m-%d %H:%M")}

class ServiceUnit(db.Model):
    __tablename__="service_units"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(150),nullable=False,unique=True)
    manager_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    manager=db.relationship("User",foreign_keys=[manager_id])
    def to_dict(self):
        return {"id":self.id,"name":self.name,"manager_id":self.manager_id}

class Category(db.Model):
    __tablename__="categories"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(150),nullable=False)
    service_unit_id=db.Column(db.Integer,db.ForeignKey("service_units.id"),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    service_unit=db.relationship("ServiceUnit",backref=db.backref("categories",lazy="dynamic"))
    def to_dict(self):
        return {"id":self.id,"name":self.name,"service_unit_id":self.service_unit_id}


CAT_DEPT={"hygiene":"Maintenance","electrical":"Electrical","transport":"Transport","maintenance":"Maintenance","safety":"Security","admin":"Administration","water":"Maintenance"}
CAT_SU_MAP={}  # Will be populated with category->service_unit_id mapping
VALID_PRI={"low","medium","high"}
VALID_STA={"routed","assigned","in-progress","resolved","escalated","closed","submitted"}


def normalize_status_value(status):
    raw = (status or "").strip().lower()
    mapping = {
        "new": "routed",
        "pending-assignment": "routed",
        "pending_assignment": "routed",
        "submitted": "submitted",
        "routed": "routed",
        "assigned": "assigned",
        "in-progress": "in-progress",
        "in_progress": "in-progress",
        "resolved": "resolved",
        "closed": "closed",
        "escalated": "escalated",
    }
    return mapping.get(raw, raw or "routed")


def media_url(path):
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        parsed = urlparse(path)
        if parsed.path.startswith("/uploads/") and has_request_context():
            return f"{request.host_url.rstrip('/')}{parsed.path}"
        return path
    base = request.host_url.rstrip("/") if has_request_context() else APP_URL.rstrip("/")
    path = path if path.startswith("/") else f"/{path}"
    return f"{base}{path}"


def gen_ticket():
    return f"TKT-{str((db.session.query(db.func.count(Complaint.id)).scalar() or 0)+1).zfill(4)}"

def allowed_file(filename, image_only=False):
    if not filename or ".." in filename or "." not in filename:
        return False
    ext = filename.rsplit(".",1)[-1].lower()
    return ext in (IMAGE_EXT if image_only else ALLOWED_EXT)

def val_phone(p): return bool(re.fullmatch(r"\d{10}",p)) if p else True

def staff_to_dict(staff):
    service_unit = db.session.get(ServiceUnit, staff.service_unit_id) if staff.service_unit_id else None
    assigned_count = Complaint.query.filter_by(assigned_staff_id=staff.id).count()
    active_count = Complaint.query.filter(
        Complaint.assigned_staff_id == staff.id,
        Complaint.status.notin_(["resolved", "closed"])
    ).count()
    data = staff.to_dict()
    data.update({
        "service_unit_name": service_unit.name if service_unit else "",
        "assigned_count": assigned_count,
        "active_count": active_count,
    })
    return data

def can_manage_staff(caller, staff=None, service_unit_id=None):
    if not caller:
        return False
    if caller.role == "admin":
        return True
    if caller.role == "service_unit_manager":
        target_service_unit_id = service_unit_id if service_unit_id is not None else (staff.service_unit_id if staff else None)
        return target_service_unit_id == caller.service_unit_id
    return False

def push_notif(uid,msg):
    try:
        db.session.add(Notification(user_id=uid,message=msg))
        db.session.commit()
    except Exception:
        db.session.rollback()

def save_upload(file,prefix="", image_only=False):
    if file and file.filename and allowed_file(file.filename, image_only=image_only):
        safe = secure_filename(file.filename)
        fname=f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{safe}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"],fname))
        return f"/uploads/{fname}"
    return None

def get_service_unit_for_category(category):
    category_ref = str(category or "").strip()
    if not category_ref:
        return None
    try:
        if category_ref.isdigit():
            cat = db.session.get(Category, int(category_ref))
        else:
            cat = Category.query.filter(db.func.lower(Category.name) == category_ref.lower()).first()
        return cat.service_unit_id if cat else None
    except Exception:
        return None


def get_category_record(category_ref):
    value = str(category_ref or "").strip()
    if not value:
        return None
    if value.isdigit():
        return db.session.get(Category, int(value))
    return Category.query.filter(db.func.lower(Category.name) == value.lower()).first()


def get_service_unit_manager(service_unit_id):
    if not service_unit_id:
        return None
    unit = db.session.get(ServiceUnit, service_unit_id)
    if unit and unit.manager_id:
        return db.session.get(User, unit.manager_id)
    return User.query.filter_by(role="service_unit_manager", service_unit_id=service_unit_id).order_by(User.id.asc()).first()


def should_escalate(complaint, now=None):
    now = now or datetime.utcnow()
    status = normalize_status_value(complaint.status)
    if complaint.is_escalated or status in {"resolved", "closed", "escalated"}:
        return False
    if not complaint.assigned_at:
        return False
    return complaint.assigned_at <= (now - timedelta(hours=48))


def notify_principal_escalation(complaint):
    principal = User.query.filter_by(role="principal").first()
    if not principal:
        return
    push_notif(principal.id, f"Issue {complaint.ticket_id} escalated after 48 hours")
    if principal.email:
        send_email(principal.email, f"🚨 Issue Escalated — {complaint.ticket_id}", email_escalation(complaint, principal.name))


def run_pending_escalations():
    try:
        now = datetime.utcnow()
        threshold = now - timedelta(hours=48)
        candidates = Complaint.query.filter(
            Complaint.assigned_at.isnot(None),
            Complaint.assigned_at <= threshold,
            Complaint.status.notin_(["resolved", "closed", "escalated"])
        ).all()
        escalated = []
        for complaint in candidates:
            if not should_escalate(complaint, now):
                continue
            complaint.is_escalated = True
            complaint.status = "escalated"
            complaint.escalated_at = complaint.escalated_at or now
            complaint.updated_at = now
            escalated.append(complaint)
        if escalated:
            db.session.commit()
            for complaint in escalated:
                notify_principal_escalation(complaint)
    except Exception:
        db.session.rollback()


def complaint_query_for_user(user, scope=None):
    role = (user.role or "").strip().lower()
    if role == "principal":
        threshold = datetime.utcnow() - timedelta(hours=48)
        return Complaint.query.filter(
            db.or_(
                Complaint.is_escalated.is_(True),
                db.and_(
                    Complaint.assigned_at.isnot(None),
                    Complaint.assigned_at <= threshold,
                    Complaint.status.notin_(["resolved", "closed"])
                ),
            )
        )
    if user.role == "service_unit_manager":
        return Complaint.query.filter_by(service_unit_id=user.service_unit_id)
    if user.role in MANAGE_ROLES:
        return Complaint.query
    if user.role == "staff":
        return Complaint.query.filter_by(assigned_staff_id=user.id)
    if user.role == "hod":
        target_dept = (user.academic_department or user.dept or "").strip()
        return Complaint.query.join(User, Complaint.user_id==User.id).filter(
            db.or_(User.academic_department == target_dept, User.dept == target_dept)
        )
    return Complaint.query.filter_by(user_id=user.id)

def check_and_escalate_complaint(complaint):
    if not should_escalate(complaint):
        return
    try:
        complaint.is_escalated = True
        complaint.escalated_at = datetime.utcnow()
        complaint.status = "escalated"
        complaint.updated_at = datetime.utcnow()
        db.session.commit()
        notify_principal_escalation(complaint)
    except Exception:
        db.session.rollback()

def can_access_complaint(user, complaint):
    if user.role in MANAGE_ROLES:
        return True
    if user.role == "principal":
        return complaint.is_escalated
    if user.role == "service_unit_manager":
        return complaint.service_unit_id == user.service_unit_id
    if user.role == "staff":
        return complaint.assigned_staff_id == user.id
    if user.role == "hod":
        reporter_dept = ""
        if complaint.reporter:
            reporter_dept = complaint.reporter.academic_department or complaint.reporter.dept or ""
        return reporter_dept == (user.academic_department or user.dept or "")
    return complaint.user_id == user.id

# EMAIL

def get_gmail():
    if MAIL_MODE == "smtp" or RENDER_ENV: return None
    if not GMAIL_API_OK or not os.path.exists(TOKEN_FILE): return None
    try:
        creds=Credentials.from_authorized_user_file(TOKEN_FILE,["https://www.googleapis.com/auth/gmail.send"])
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            open(TOKEN_FILE,"w").write(creds.to_json())
        return build("gmail","v1",credentials=creds) if creds.valid else None
    except Exception:
        return None

def send_email(to,subj,html):
    msg=MIMEMultipart("alternative")
    msg["Subject"]=subj
    msg["From"]=f"CDGI CIRS <{EMAIL_FROM or SMTP_USER}>"
    msg["To"]=to
    msg.attach(MIMEText(html,"html"))
    svc=get_gmail()
    if svc:
        try:
            raw=base64.urlsafe_b64encode(msg.as_bytes()).decode()
            svc.users().messages().send(userId="me",body={"raw":raw}).execute()
            return True, "gmail_api", ""
        except Exception as e:
            gmail_err=str(e)
    else:
        gmail_err="gmail_token.json missing or Gmail API unavailable"
    if SMTP_OK:
        try:
            with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=20) as s:
                s.ehlo(); s.starttls(); s.login(SMTP_USER,SMTP_PASS)
                s.sendmail(EMAIL_FROM,[to],msg.as_string())
            return True, "smtp", ""
        except Exception as e:
            return False, "smtp", str(e)
    return False, "none", gmail_err

def tpl_base(header_bg,header_txt,body):
    return f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
<div style="background:{header_bg};padding:20px 28px;text-align:center;">
<div style="font-size:36px;margin-bottom:6px;">🏛️</div>
<h2 style="color:#fff;margin:0;font-size:18px;">{header_txt}</h2>
<p style="color:rgba(255,255,255,.75);margin:4px 0 0;font-size:12px;">Chameli Devi Group of Institutions, Indore M.P.</p>
</div>
<div style="padding:24px 28px;background:#fff;">{body}</div>
<div style="background:#f8fafc;padding:10px;text-align:center;"><p style="color:#94a3b8;font-size:11px;margin:0;">CDGI CIRS · Automated Notification · Indore 452020</p></div>
</div>"""

def email_verify(name,url):
    body=f"<p>Dear <strong>{name}</strong>, please verify your email to activate your CDGI CIRS account.</p><div style='text-align:center;margin:24px 0;'><a href='{url}' style='background:linear-gradient(135deg,#1a4faa,#2563eb);color:#fff;padding:13px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;'>✅ Verify My Email</a></div><p style='color:#6b7280;font-size:12px;'>Link expires in 24 hours. If you didn't register, ignore this email.</p>"
    return tpl_base("linear-gradient(135deg,#1a4faa,#0f3485)","Verify Your Email Address",body)

def email_received(name,tid,title,cat,service_unit_name):
    body=f"<p>Dear <strong>{name}</strong>, your complaint has been routed successfully.</p><p><strong>Ticket:</strong> {tid}<br><strong>Issue:</strong> {title}<br><strong>Category:</strong> {cat}<br><strong>Service Unit:</strong> {service_unit_name}<br><strong>Status:</strong> Routed</p>"
    return tpl_base("linear-gradient(135deg,#1a4faa,#0f766e)","Complaint Routed",body)

def email_assigned(staff_name, ticket_id, title):
    body=f"<p>Dear <strong>{staff_name}</strong>, a new issue has been assigned to you.</p><p><strong>Ticket:</strong> {ticket_id}<br><strong>Issue:</strong> {title}<br><strong>Status:</strong> Assigned</p><p>Please log in and update the progress.</p>"
    return tpl_base("linear-gradient(135deg,#7c3aed,#2563eb)","New Issue Assigned",body)

def email_resolved(name,tid,title,by,after_urls=None):
    imgs = "".join([f'<img src="{u}" style="max-width:100%;border-radius:8px;border:2px solid #bbf7d0;margin-top:8px;" alt="Resolved"/>' for u in (after_urls or [])[:3]])
    body=f"<p>Dear <strong>{name}</strong>, your issue has been resolved.</p><p><strong>Ticket:</strong> {tid}<br><strong>Issue:</strong> {title}<br><strong>Resolved By:</strong> {by}</p>{imgs}<p>Please log in to verify and rate the resolution.</p>"
    return tpl_base("linear-gradient(135deg,#166534,#15803d)","Issue Successfully Resolved!",body)

def email_escalation(complaint, principal_name):
    staff_info = complaint.assigned_staff.name if complaint.assigned_staff else "Not assigned yet"
    manager = complaint.assigned_by_manager or get_service_unit_manager(complaint.service_unit_id)
    manager_name = manager.name if manager else "Unknown Manager"
    su_name = complaint.service_unit.name if complaint.service_unit else "Unknown Unit"
    student_dept = (complaint.reporter.academic_department or complaint.reporter.dept) if complaint.reporter else "Unknown Department"
    
    body = f"""<p>Dear <strong>{principal_name}</strong>,</p>
    <p>An issue has been escalated due to crossing the 48-hour service window.</p>
    <p><strong>Issue Details:</strong><br>
    Ticket: {complaint.ticket_id}<br>
    Title: {complaint.title}<br>
    Category: {complaint.category.capitalize()}<br>
    Service Unit: {su_name}<br>
    Student Name: {complaint.reporter.name if complaint.reporter else 'Unknown'}<br>
    Student Department: {student_dept}<br>
    Assigned Staff: {staff_info}<br>
    Status: Escalated</p>
    <p>Please review this issue and take necessary action.</p>"""
    return tpl_base("linear-gradient(135deg,#dc2626,#991b1b)","Issue Escalated - 48 Hour Threshold",body)

@app.route("/")
def index(): return send_from_directory(app.static_folder, "index.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename): return send_from_directory(app.config["UPLOAD_FOLDER"],filename)

@app.route("/verify-email")
def verify_email_page():
    token=request.args.get("token","")
    user=User.query.filter_by(verify_token=token).first()
    if not user: return "<html><body style='font-family:Arial;text-align:center;padding:60px;'><h2 style='color:#dc2626;'>❌ Invalid link</h2></body></html>"
    if user.verify_expires and datetime.utcnow()>user.verify_expires:
        return "<html><body style='font-family:Arial;text-align:center;padding:60px;'><h2 style='color:#d97706;'>⚠️ Link expired. Request new verification.</h2></body></html>"
    user.is_verified=True; user.verify_token=None; user.verify_expires=None
    db.session.commit()
    return """<html><head><meta http-equiv="refresh" content="3;url=/"></head><body style="font-family:Arial;text-align:center;padding:60px;background:#f0fdf4;"><div style="font-size:60px;">✅</div><h2 style="color:#166534;">Email Verified!</h2><p>Redirecting to login in 3 seconds…</p></body></html>"""

@app.route("/api/register",methods=["POST"])
def register():
    data=request.get_json() or {}
    for f in ["name","email","password"]:
        if not data.get(f,"").strip(): return jsonify({"error":f"Field '{f}' required"}),400
    phone=data.get("phone","").strip()
    if phone and not val_phone(phone): return jsonify({"error":"Phone must be 10 digits"}),400
    if len(data["password"])<6: return jsonify({"error":"Password min 6 chars"}),400
    email=data["email"].lower().strip()
    if User.query.filter_by(email=email).first(): return jsonify({"error":"Email already registered"}),409
    role = (data.get("role","student") or "student").strip().lower()
    if role not in ("student","faculty"):
        return jsonify({"error":"Only student and faculty can self-register. Staff accounts are created by managers."}), 403
    vtok=secrets.token_urlsafe(32); vexp=datetime.utcnow()+timedelta(hours=24)
    auto_verified = (not EMAIL_VERIFY_ENABLED) or AUTO_VERIFY_USERS
    user=User(name=data["name"].strip(),email=email,password=generate_password_hash(data["password"]),
              role=role,dept=data.get("dept","CSE"),roll_no=data.get("roll_no",""),phone=phone,
              academic_department=data.get("dept","CSE"),
              is_verified=auto_verified,
              verify_token=vtok if (EMAIL_VERIFY_ENABLED and not auto_verified) else None,
              verify_expires=vexp if (EMAIL_VERIFY_ENABLED and not auto_verified) else None)
    db.session.add(user); db.session.commit()
    if EMAIL_VERIFY_ENABLED and not auto_verified:
        sent, provider, err = send_email(email,"✉️ Verify Your Email | CDGI CIRS",email_verify(user.name,f"{APP_URL}/verify-email?token={vtok}"))
        if not sent:
            return jsonify({"error":f"Account created, but verification email could not be sent. {err or 'Check Gmail/SMTP setup and try resend.'}","need_verify":True}),500
        return jsonify({"status":"pending_verification","message":"Verification email sent successfully.","email_provider":provider}),201
    token=create_access_token(identity=str(user.id))
    return jsonify({"status":"success","token":token,"user":user.to_dict()}),201

@app.route("/api/resend-verify",methods=["POST"])
def resend_verify():
    data=request.get_json() or {}; email=data.get("email","").lower().strip()
    user=User.query.filter_by(email=email).first()
    if not user: return jsonify({"error":"Email not found"}),404
    if user.is_verified: return jsonify({"message":"Already verified."}),200
    tok=secrets.token_urlsafe(32); user.verify_token=tok; user.verify_expires=datetime.utcnow()+timedelta(hours=24)
    db.session.commit()
    sent, provider, err = send_email(email,"✉️ Verify Your Email | CDGI CIRS",email_verify(user.name,f"{APP_URL}/verify-email?token={tok}"))
    if not sent:
        return jsonify({"error":f"Verification email could not be sent. {err or 'Check Gmail/SMTP setup.'}"}),500
    return jsonify({"status":"success","message":"Verification email sent.","email_provider":provider})

@app.route("/api/login",methods=["POST"])
def login():
    data=request.get_json() or {}
    if not data.get("email") or not data.get("password"): return jsonify({"error":"Email and password required"}),400
    user=User.query.filter_by(email=data["email"].lower().strip()).first()
    if not user or not check_password_hash(user.password,data["password"]): return jsonify({"error":"Invalid email or password"}),401
    if EMAIL_VERIFY_ENABLED and not user.is_verified: return jsonify({"error":"Please verify your email first. Check your inbox.","need_verify":True}),403
    token=create_access_token(identity=str(user.id))
    return jsonify({"status":"success","token":token,"user":user.to_dict()})

@app.route("/api/me",methods=["GET"])
@jwt_required()
def me():
    user=db.session.get(User,int(get_jwt_identity()))
    return jsonify(user.to_dict()) if user else (jsonify({"error":"Not found"}),404)

@app.route("/api/profile",methods=["PUT"])
@jwt_required()
def update_profile():
    user=db.session.get(User,int(get_jwt_identity()))
    if not user: return jsonify({"error":"Not found"}),404
    data=request.get_json() or {}
    if data.get("name"): user.name=data["name"].strip()
    p=data.get("phone","").strip()
    if p:
        if not val_phone(p): return jsonify({"error":"Phone must be 10 digits"}),400
        user.phone=p
    if data.get("password"):
        if len(data["password"])<6: return jsonify({"error":"Password min 6 chars"}),400
        user.password=generate_password_hash(data["password"])
    db.session.commit()
    return jsonify({"status":"success","user":user.to_dict()})

@app.route("/api/staff/options", methods=["GET"])
@jwt_required()
def get_staff_options():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role != "service_unit_manager":
        return jsonify({"error": "Access denied"}), 403

    staff = User.query.filter_by(role="staff", service_unit_id=user.service_unit_id).order_by(User.name.asc()).all()
    return jsonify({"status":"success", "data":[s.to_dict() for s in staff]})

@app.route("/api/manager/staff", methods=["GET"])
@jwt_required()
def get_manager_staff():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role != "service_unit_manager":
        return jsonify({"error": "Access denied"}), 403
    
    staff = User.query.filter_by(role="staff", service_unit_id=user.service_unit_id).order_by(User.name.asc()).all()
    data = [{"id": s.id, "name": s.name, "email": s.email, "service_unit_id": s.service_unit_id} for s in staff]
    
    if not data:
        return jsonify({"status":"success", "data": [], "message": "No staff found for this unit"})
    return jsonify({"status":"success", "data": data})

@app.route("/api/service-units", methods=["GET"])
@jwt_required()
def get_service_units():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role not in ("admin", "service_unit_manager"):
        return jsonify({"error":"Access denied"}),403
    q = ServiceUnit.query
    if user.role == "service_unit_manager":
        q = q.filter_by(id=user.service_unit_id)
    units = q.order_by(ServiceUnit.name.asc()).all()
    return jsonify({"status":"success", "data":[u.to_dict() for u in units]})

@app.route("/api/staff-members", methods=["GET"])
@jwt_required()
def list_staff_members():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role not in ("admin", "service_unit_manager"):
        return jsonify({"error":"Access denied"}),403
    q = User.query.filter_by(role="staff")
    if user.role == "service_unit_manager":
        q = q.filter_by(service_unit_id=user.service_unit_id)
    staff = q.order_by(User.created_at.desc()).all()
    return jsonify({"status":"success", "data":[staff_to_dict(s) for s in staff]})

@app.route("/api/staff-members", methods=["POST"])
@jwt_required()
def create_staff_member():
    caller = db.session.get(User, int(get_jwt_identity()))
    if not caller or caller.role not in ("admin", "service_unit_manager"):
        return jsonify({"error":"Access denied"}),403
    data = request.get_json() or {}
    name = data.get("name","").strip()
    email = data.get("email","").lower().strip()
    password = data.get("password","").strip()
    phone = data.get("phone","").strip()
    dept = data.get("dept","").strip()
    service_unit_id = data.get("service_unit_id")
    if caller.role == "service_unit_manager":
        service_unit_id = caller.service_unit_id
    if not name or not email or not password:
        return jsonify({"error":"Name, email and password required"}),400
    if len(password) < 6:
        return jsonify({"error":"Password must be at least 6 characters"}),400
    if phone and not val_phone(phone):
        return jsonify({"error":"Phone must be 10 digits"}),400
    if User.query.filter_by(email=email).first():
        return jsonify({"error":"Email already registered"}),409
    try:
        service_unit_id = int(service_unit_id)
    except Exception:
        return jsonify({"error":"Service unit required"}),400
    unit = db.session.get(ServiceUnit, service_unit_id)
    if not unit or not can_manage_staff(caller, service_unit_id=service_unit_id):
        return jsonify({"error":"Invalid service unit"}),403
    staff = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        role="staff",
        dept=dept or unit.name,
        phone=phone,
        is_verified=True,
        service_unit_id=service_unit_id,
        academic_department=dept or unit.name,
    )
    db.session.add(staff)
    db.session.commit()
    return jsonify({"status":"success","message":f"Staff member {staff.name} added","staff":staff_to_dict(staff)}),201

@app.route("/api/staff-members/<int:staff_id>", methods=["PUT"])
@jwt_required()
def update_staff_member(staff_id):
    caller = db.session.get(User, int(get_jwt_identity()))
    staff = db.session.get(User, staff_id)
    if not staff or staff.role != "staff":
        return jsonify({"error":"Staff member not found"}),404
    if not can_manage_staff(caller, staff=staff):
        return jsonify({"error":"Access denied"}),403
    data = request.get_json() or {}
    if data.get("name"):
        staff.name = data["name"].strip()
    if "phone" in data:
        phone = (data.get("phone") or "").strip()
        if phone and not val_phone(phone):
            return jsonify({"error":"Phone must be 10 digits"}),400
        staff.phone = phone
    if data.get("dept"):
        staff.dept = data["dept"].strip()
        staff.academic_department = data["dept"].strip()
    if data.get("password"):
        if len(data["password"]) < 6:
            return jsonify({"error":"Password must be at least 6 characters"}),400
        staff.password = generate_password_hash(data["password"])
    if caller.role == "admin" and data.get("service_unit_id"):
        unit = db.session.get(ServiceUnit, int(data["service_unit_id"]))
        if not unit:
            return jsonify({"error":"Invalid service unit"}),400
        staff.service_unit_id = unit.id
    db.session.commit()
    return jsonify({"status":"success","message":f"Staff member {staff.name} updated","staff":staff_to_dict(staff)})

@app.route("/api/staff-members/<int:staff_id>", methods=["DELETE"])
@jwt_required()
def delete_staff_member(staff_id):
    caller = db.session.get(User, int(get_jwt_identity()))
    staff = db.session.get(User, staff_id)
    if not staff or staff.role != "staff":
        return jsonify({"error":"Staff member not found"}),404
    if not can_manage_staff(caller, staff=staff):
        return jsonify({"error":"Access denied"}),403
    reassigned = 0
    for complaint in Complaint.query.filter_by(assigned_staff_id=staff.id).all():
        if normalize_status_value(complaint.status) in {"resolved", "closed"}:
            complaint.assigned_staff_id = None
        else:
            complaint.assigned_staff_id = None
            complaint.assigned_to = ""
            complaint.assigned_at = None
            complaint.assigned_by_manager_id = None
            complaint.status = "routed"
            reassigned += 1
        complaint.updated_at = datetime.utcnow()
    db.session.delete(staff)
    db.session.commit()
    msg = f"Staff member {staff.name} deleted"
    if reassigned:
        msg += f"; {reassigned} active issue(s) returned to routed"
    return jsonify({"status":"success","message":msg})

@app.route("/api/categories", methods=["GET"])
def get_categories():
    categories = Category.query.order_by(Category.name.asc()).all()
    return jsonify({
        "status":"success",
        "data":[
            {
                "id": c.id,
                "name": c.name,
                "service_unit_id": c.service_unit_id,
                "service_unit_name": c.service_unit.name if c.service_unit else "",
            }
            for c in categories
        ],
        "count": len(categories)
    })

@app.route("/api/complaints",methods=["GET"])
@jwt_required()
def get_complaints():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user: return jsonify({"error":"Not found"}),404
    run_pending_escalations()
    q=complaint_query_for_user(user, request.args.get("scope"))
    st=request.args.get("status"); cat=request.args.get("category"); srch=request.args.get("search")
    if st: q=q.filter(Complaint.status == st)
    if cat: q=q.filter(Complaint.category == cat)
    if srch: q=q.filter(db.or_(Complaint.title.ilike(f"%{srch}%"),Complaint.ticket_id.ilike(f"%{srch}%")))
    complaints=q.order_by(Complaint.created_at.desc()).all()
    return jsonify({"status":"success","data":[c.to_dict(user) for c in complaints],"count":len(complaints)})

@app.route("/api/staff/issues",methods=["GET"])
@jwt_required()
def get_staff_issues():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role != "staff":
        return jsonify({"error":"Access denied"}), 403
    complaints = Complaint.query.filter_by(assigned_staff_id=user.id).order_by(Complaint.created_at.desc()).all()
    return jsonify({"status":"success", "data":[c.to_dict(user) for c in complaints], "count": len(complaints)})

@app.route("/api/complaints",methods=["POST"])
@jwt_required()
def create_complaint():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user: return jsonify({"error":"Not found"}),404
    if user.role not in REPORTER_ROLES:
        return jsonify({"error":"Only student and faculty users can report issues"}),403
    title=request.form.get("title","").strip()
    category_ref=(request.form.get("category_id") or request.form.get("category") or "").strip()
    desc=request.form.get("description","").strip(); location=request.form.get("location","").strip()
    if not title or not category_ref or not desc: return jsonify({"error":"Title, category and description required"}),400
    category = get_category_record(category_ref)
    if not category:
        return jsonify({"error":"Invalid category_id"}),400
    service_unit = db.session.get(ServiceUnit, category.service_unit_id)
    if not service_unit:
        return jsonify({"error":"Selected category is not mapped to a service unit"}),400

    c=Complaint(ticket_id=gen_ticket(),title=title,category=category.name,description=desc,
                location=location,dept=service_unit.name,user_id=uid,status="routed",
                service_unit_id=service_unit.id)
    db.session.add(c); db.session.flush()
    uploaded = []
    files = request.files.getlist("images") or []
    if not files and "image" in request.files:
        files = [request.files["image"]]
    for file in files:
        saved = save_upload(file, prefix=f"issue_{c.ticket_id}", image_only=True)
        if saved:
            uploaded.append(saved)
            if not c.image_before:
                c.image_before = (saved)
            db.session.add(IssueImage(complaint_id=c.id, image_path=saved, uploaded_by=user.role))
    if uploaded:
        c.image_before = uploaded[0]
    db.session.commit()
    manager = get_service_unit_manager(service_unit.id)
    if manager:
        push_notif(manager.id,f"New routed complaint {c.ticket_id}: {title}")
        if manager.email:
            send_email(
                manager.email,
                f"📌 New Complaint Routed — {c.ticket_id}",
                tpl_base(
                    "linear-gradient(135deg,#0f766e,#1a4faa)",
                    "New Complaint Routed To Your Service Unit",
                    f"<p>Dear <strong>{manager.name}</strong>,</p><p>A new complaint has been routed to <strong>{service_unit.name}</strong>.</p><p><strong>Ticket:</strong> {c.ticket_id}<br><strong>Issue:</strong> {c.title}<br><strong>Reporter:</strong> {user.name}<br><strong>Status:</strong> Routed</p>",
                ),
            )
    sent, provider, err = send_email(user.email,f"✅ Complaint {c.ticket_id} Routed | CDGI CIRS",email_received(user.name,c.ticket_id,title,category.name,service_unit.name))
    msg=f"Complaint {c.ticket_id} routed to {service_unit.name}."
    if sent: msg+=f" Confirmation email sent via {provider}."
    else: msg+=f" Saved successfully, but confirmation email failed: {err or 'mail service unavailable'}."
    return jsonify({"status":"success","message":msg,"email_sent":sent,"complaint":c.to_dict(user)}),201

@app.route("/api/complaints/<ticket_id>",methods=["GET"])
@jwt_required()
def get_complaint(ticket_id):
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    c=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}),404
    check_and_escalate_complaint(c)
    if not can_access_complaint(user, c): return jsonify({"error":"Unauthorized"}),403
    return jsonify(c.to_dict(user))

@app.route("/api/complaints/<ticket_id>/assign", methods=["POST"])
@jwt_required()
def assign_complaint(ticket_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role not in ASSIGN_ROLES:
        return jsonify({"error":"Only service unit managers can assign issues"}), 403
    
    complaint = Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not complaint:
        return jsonify({"error":"Not found"}), 404
    
    if complaint.service_unit_id != user.service_unit_id:
        return jsonify({"error":"You can only assign complaints from your service unit"}), 403
    
    data = request.get_json() or {}
    staff_id = data.get("assigned_staff_id")
    if not staff_id:
        return jsonify({"error":"assigned_staff_id required"}), 400
    
    staff = db.session.get(User, int(staff_id))
    if not staff or staff.role != "staff":
        return jsonify({"error":"Selected user is not a valid staff member"}), 400
    
    if staff.service_unit_id != user.service_unit_id:
        return jsonify({"error":"You can only assign staff from your service unit"}), 403
    
    complaint.assigned_staff_id = staff.id
    complaint.assigned_by_manager_id = user.id
    complaint.assigned_to = staff.name
    complaint.assigned_at = datetime.utcnow()
    complaint.status = "assigned"
    complaint.updated_at = datetime.utcnow()
    db.session.commit()
    push_notif(staff.id, f"{complaint.ticket_id} assigned to you by {user.name}")
    push_notif(complaint.user_id, f"{complaint.ticket_id} assigned to staff: {staff.name}")
    send_email(staff.email, f"📌 Issue Assigned — {complaint.ticket_id}", email_assigned(staff.name, complaint.ticket_id, complaint.title))
    return jsonify({"status":"success", "message":f"{complaint.ticket_id} assigned to {staff.name}", "complaint": complaint.to_dict(user)})

@app.route("/api/complaints/<ticket_id>",methods=["PUT"])
@jwt_required()
def update_complaint(ticket_id):
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    c=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}),404
    if not can_access_complaint(user, c):
        return jsonify({"error":"Unauthorized"}),403
    
    # Check for escalation
    check_and_escalate_complaint(c)
    
    data=request.get_json() or {}
    old=c.status
    
    if "feedback" in data and c.user_id==uid and normalize_status_value(c.status)=="resolved":
        r=int(data["feedback"])
        if not 1<=r<=5: return jsonify({"error":"Rating 1-5"}),400
        c.feedback=r; db.session.commit()
        return jsonify({"status":"success","message":"Feedback submitted!"})

    if user.role in {"principal", "hod", "admin", "coordinator", "faculty", "student"}:
        return jsonify({"error":"You cannot update complaint workflow from this account"}), 403

    if user.role == "service_unit_manager":
        return jsonify({"error":"Managers assign issues to staff. Staff update work progress."}), 403

    if user.role == "staff" and c.assigned_staff_id == user.id:
        if "status" in data:
            next_status = normalize_status_value(data["status"])
            if next_status not in {"assigned", "in-progress", "resolved"}:
                return jsonify({"error":"Invalid status"}),400
            c.status=next_status
        if "resolved_by" in data:
            c.resolved_by=data["resolved_by"]
        if c.status == "resolved" and not c.resolved_by:
            c.resolved_by = user.name
        c.updated_at=datetime.utcnow(); db.session.commit()
        reporter=db.session.get(User,c.user_id)
        mail_msg=""
        if reporter and c.status!=old:
            if c.status=="resolved":
                urls = [img.to_dict()["image_url"] for img in c.resolution_images.order_by(ResolutionImage.created_at.asc()).all()]
                sent, provider, err = send_email(reporter.email,f"✅ Issue Resolved — {ticket_id} | CDGI CIRS", email_resolved(reporter.name,ticket_id,c.title,c.resolved_by or user.name,urls))
            else:
                sent, provider, err = send_email(reporter.email,f"📢 Complaint Update — {ticket_id}", f"<p>Dear {reporter.name}, complaint {ticket_id} is now <strong>{c.status}</strong>.</p>")
            mail_msg=f" Email sent via {provider}." if sent else f" Email failed: {err or 'mail service unavailable'}."
        if c.assigned_staff_id:
            push_notif(c.assigned_staff_id, f"{ticket_id} → {c.status}")
        push_notif(c.user_id,f"Complaint {ticket_id} → {c.status}")
        return jsonify({"status":"success","message":f"Complaint {ticket_id} updated to {c.status}.{mail_msg}","complaint":c.to_dict(user)})
    return jsonify({"error":"Unauthorized"}),403

@app.route("/api/complaints/<ticket_id>/issue-images", methods=["POST"])
@jwt_required()
def upload_issue_images(ticket_id):
    user = db.session.get(User, int(get_jwt_identity()))
    complaint = Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not complaint: return jsonify({"error":"Not found"}),404
    if complaint.user_id != user.id and user.role not in MANAGE_ROLES:
        return jsonify({"error":"Unauthorized"}),403
    files = request.files.getlist("images")
    if not files: return jsonify({"error":"No images"}),400
    added = []
    for file in files:
        saved = save_upload(file, prefix=f"issue_{ticket_id}", image_only=True)
        if saved:
            db.session.add(IssueImage(complaint_id=complaint.id, image_path=saved, uploaded_by=user.role))
            added.append(saved)
    if not added: return jsonify({"error":"Invalid files"}),400
    if not complaint.image_before:
        complaint.image_before = added[0]
    db.session.commit()
    return jsonify({"status":"success", "complaint": complaint.to_dict(user)})

@app.route("/api/complaints/<ticket_id>/resolution-images",methods=["POST"])
@jwt_required()
def upload_resolution_images(ticket_id):
    user=db.session.get(User,int(get_jwt_identity()))
    complaint=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not complaint: return jsonify({"error":"Not found"}),404
    if user.role != "staff" or complaint.assigned_staff_id != user.id:
        return jsonify({"error":"Unauthorized"}),403
    files = request.files.getlist("images") or []
    if not files and "image_after" in request.files:
        files = [request.files["image_after"]]
    if not files: return jsonify({"error":"No image"}),400
    added = []
    for file in files:
        saved = save_upload(file, prefix=f"resolution_{ticket_id}", image_only=True)
        if saved:
            db.session.add(ResolutionImage(complaint_id=complaint.id, image_path=saved, uploaded_by_staff_id=user.id))
            added.append(saved)
    if not added: return jsonify({"error":"Invalid file"}),400
    complaint.image_after = added[0]
    complaint.resolved_by = user.name
    complaint.status = "resolved"
    complaint.updated_at=datetime.utcnow()
    db.session.commit()
    reporter=db.session.get(User,complaint.user_id)
    sent=False; provider=""; err=""
    if reporter:
        urls = [media_url(path) for path in added]
        sent, provider, err = send_email(reporter.email,f"✅ Issue Resolved — {ticket_id} | CDGI CIRS", email_resolved(reporter.name,ticket_id,complaint.title,user.name,urls))
    push_notif(complaint.user_id,f"✅ {ticket_id} resolved by {user.name}")
    return jsonify({"status":"success","message":f"Resolution images uploaded for {ticket_id}.","email_sent": sent, "complaint":complaint.to_dict(user)})

@app.route("/api/complaints/<ticket_id>/after-photo",methods=["POST"])
@jwt_required()
def upload_after_photo(ticket_id):
    return upload_resolution_images(ticket_id)

@app.route("/api/complaints/<ticket_id>",methods=["DELETE"])
@jwt_required()
def delete_complaint(ticket_id):
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    c=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}),404
    if user.role!="admin" and c.user_id!=uid: return jsonify({"error":"Unauthorized"}),403
    for img in [c.image_before,c.image_after]:
        if img:
            try:
                fp=os.path.join(app.config["UPLOAD_FOLDER"],img.split("/uploads/")[-1])
                if os.path.exists(fp): os.remove(fp)
            except Exception:
                pass
    db.session.delete(c); db.session.commit()
    return jsonify({"status":"success","message":f"{ticket_id} deleted"})

@app.route("/api/stats",methods=["GET"])
@jwt_required()
def get_stats():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user: return jsonify({"error":"Not found"}),404
    run_pending_escalations()
    base=complaint_query_for_user(user)
    total = base.count()
    pending = base.filter(Complaint.status.in_(["routed","submitted","pending-assignment"])).count()
    assigned = base.filter(Complaint.status == "assigned").count()
    inp = base.filter(Complaint.status == "in-progress").count()
    res = base.filter(Complaint.status == "resolved").count()
    cats = {}
    for c in base.all():
        cats[c.category] = cats.get(c.category, 0) + 1
    return jsonify({"total":total,"pending_assignment":pending,"assigned":assigned,"new":pending,
                    "in_progress":inp,"resolved":res,"categories":cats,
                    "total_users":User.query.count() if user.role=="admin" else None,
                    "resolution_rate":round((res/total*100) if total else 0,1)})

@app.route("/api/users",methods=["GET"])
@jwt_required()
def get_users():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user or user.role not in ("admin","coordinator"): return jsonify({"error":"Access denied"}),403
    return jsonify({"status":"success","data":[u.to_dict() for u in User.query.order_by(User.created_at.desc()).all()]})

@app.route("/api/users/<int:uid>/role",methods=["PUT"])
@jwt_required()
def update_role(uid):
    caller=db.session.get(User,int(get_jwt_identity()))
    if not caller or caller.role!="admin": return jsonify({"error":"Admin only"}),403
    target=db.session.get(User,uid)
    if not target: return jsonify({"error":"Not found"}),404
    data=request.get_json() or {}
    if data.get("role") in {"student","faculty","staff","coordinator","admin"}:
        target.role=data["role"]; db.session.commit()
    return jsonify({"status":"success","user":target.to_dict()})

@app.route("/api/users/<int:uid>",methods=["DELETE"])
@jwt_required()
def delete_user(uid):
    caller=db.session.get(User,int(get_jwt_identity()))
    if not caller or caller.role!="admin": return jsonify({"error":"Admin only"}),403
    if caller.id==uid: return jsonify({"error":"Cannot delete own account"}),400
    target=db.session.get(User,uid)
    if not target: return jsonify({"error":"Not found"}),404
    db.session.delete(target); db.session.commit()
    return jsonify({"status":"success","message":f"User {target.name} deleted"})

@app.route("/api/notifications",methods=["GET"])
@jwt_required()
def get_notifications():
    uid=int(get_jwt_identity())
    ns=Notification.query.filter_by(user_id=uid).order_by(Notification.created_at.desc()).limit(20).all()
    unread=Notification.query.filter_by(user_id=uid,is_read=False).count()
    return jsonify({"data":[n.to_dict() for n in ns],"unread":unread})

@app.route("/api/notifications/read-all",methods=["PUT"])
@jwt_required()
def mark_all_read():
    uid=int(get_jwt_identity())
    Notification.query.filter_by(user_id=uid,is_read=False).update({"is_read":True})
    db.session.commit(); return jsonify({"status":"success"})

def run_migrations():
    inspector = db.inspect(db.engine)
    cols = {c['name'] for c in inspector.get_columns('complaints')} if inspector.has_table('complaints') else set()
    users_cols = {c['name'] for c in inspector.get_columns('users')} if inspector.has_table('users') else set()
    dialect = db.engine.dialect.name
    timestamp_type = "TIMESTAMP" if "postgres" in dialect else "DATETIME"
    stmts = []
    
    # Add missing columns to complaints table
    if 'assigned_staff_id' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN assigned_staff_id INTEGER')
    if 'image_before' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN image_before VARCHAR(300)')
    if 'image_after' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN image_after VARCHAR(300)')
    if 'resolved_by' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN resolved_by VARCHAR(150)')
    if 'service_unit_id' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN service_unit_id INTEGER')
    if 'is_escalated' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN is_escalated BOOLEAN DEFAULT FALSE')
    if 'escalated_at' not in cols:
        stmts.append(f'ALTER TABLE complaints ADD COLUMN escalated_at {timestamp_type}')
    if 'assigned_at' not in cols:
        stmts.append(f'ALTER TABLE complaints ADD COLUMN assigned_at {timestamp_type}')
    if 'assigned_by_manager_id' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN assigned_by_manager_id INTEGER')
    
    # Add missing columns to users table
    if 'is_verified' not in users_cols:
        stmts.append('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT TRUE')
    if 'verify_token' not in users_cols:
        stmts.append('ALTER TABLE users ADD COLUMN verify_token VARCHAR(100)')
    if 'verify_expires' not in users_cols:
        stmts.append(f'ALTER TABLE users ADD COLUMN verify_expires {timestamp_type}')
    if 'service_unit_id' not in users_cols:
        stmts.append('ALTER TABLE users ADD COLUMN service_unit_id INTEGER')
    if 'academic_department' not in users_cols:
        stmts.append('ALTER TABLE users ADD COLUMN academic_department VARCHAR(100)')
    
    for stmt in stmts:
        try:
            db.session.execute(db.text(stmt))
            db.session.commit()
            print(f"✓ Migration: {stmt}")
        except Exception as e:
            db.session.rollback()
            print(f"Migration skipped (already exists): {stmt[:50]}...")
    
    # data backfill
    try:
        db.session.execute(db.text("UPDATE complaints SET status='routed' WHERE status IN ('new','pending-assignment') OR status IS NULL"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(db.text("UPDATE complaints SET status='assigned' WHERE LOWER(status)='assigned'"))
        db.session.execute(db.text("UPDATE complaints SET status='in-progress' WHERE LOWER(status) IN ('in_progress','in-progress')"))
        db.session.execute(db.text("UPDATE complaints SET status='resolved' WHERE LOWER(status)='resolved'"))
        db.session.execute(db.text("UPDATE complaints SET status='closed' WHERE LOWER(status)='closed'"))
        db.session.execute(db.text("UPDATE complaints SET status='escalated' WHERE LOWER(status)='escalated'"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(db.text("UPDATE users SET academic_department=dept WHERE academic_department IS NULL AND role IN ('student','faculty','hod')"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    # auto-verify users for local/dev if enabled
    if AUTO_VERIFY_USERS:
        try:
            db.session.execute(db.text("UPDATE users SET is_verified=1 WHERE is_verified=0 OR is_verified IS NULL"))
            db.session.commit()
        except Exception:
            db.session.rollback()

def upsert_user(email, name, role, dept="CSE", roll_no="", phone="", service_unit_id=None, academic_department=None, password=None):
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password or DEFAULT_SEED_PASSWORD),
            role=role,
            dept=dept,
            roll_no=roll_no,
            phone=phone,
            is_verified=True,
            service_unit_id=service_unit_id,
            academic_department=academic_department,
        )
        db.session.add(user)
        db.session.commit()
        return user
    # Update existing user if needed
    user.name = name or user.name
    user.role = role or user.role
    if dept:
        user.dept = dept
    if roll_no:
        user.roll_no = roll_no
    if phone:
        user.phone = phone
    if service_unit_id is not None:
        user.service_unit_id = service_unit_id
    if academic_department is not None:
        user.academic_department = academic_department
    if password and SEED_RESET_PASSWORDS:
        user.password = generate_password_hash(password)
    if AUTO_VERIFY_USERS:
        user.is_verified = True
    db.session.commit()
    return user


def backfill_complaint_routing():
    try:
        categories = {
            cat.name.lower(): cat.service_unit_id
            for cat in Category.query.all()
            if cat.service_unit_id
        }
        changed = False
        for complaint in Complaint.query.filter(
            db.or_(Complaint.service_unit_id.is_(None), Complaint.status.in_(["pending-assignment", "new"]))
        ).all():
            mapped_service_unit_id = categories.get((complaint.category or "").strip().lower())
            if not mapped_service_unit_id:
                continue
            if not complaint.service_unit_id:
                complaint.service_unit_id = mapped_service_unit_id
            complaint.status = normalize_status_value(complaint.status)
            if not complaint.dept:
                service_unit = db.session.get(ServiceUnit, mapped_service_unit_id)
                complaint.dept = service_unit.name if service_unit else complaint.dept
            changed = True
        if changed:
            db.session.commit()
    except Exception:
        db.session.rollback()

def seed_default_accounts():
    if not SEED_DEFAULT_USERS:
        return
    # Admin
    upsert_user(
        email="admin@cdgi.edu.in",
        name="Admin CDGI",
        role="admin",
        dept="CSE",
        roll_no="ADMIN001",
        phone="0000000000",
        password=os.getenv("ADMIN_PASSWORD", "admin123"),
    )
    # Principal
    upsert_user(
        email="principal@cdgi.edu.in",
        name="Principal CDGI",
        role="principal",
        dept="Administration",
        password=DEFAULT_SEED_PASSWORD,
    )
    # HODs
    upsert_user(
        email="hod.cse@cdgi.edu.in",
        name="HOD CSE",
        role="hod",
        dept="CSE",
        academic_department="CSE",
        password=DEFAULT_SEED_PASSWORD,
    )
    upsert_user(
        email="hod.it@cdgi.edu.in",
        name="HOD IT",
        role="hod",
        dept="IT",
        academic_department="IT",
        password=DEFAULT_SEED_PASSWORD,
    )
    # Demo student
    upsert_user(
        email="student@cirs.local",
        name="Demo Student",
        role="student",
        dept="CSE",
        roll_no="CSE0001",
        phone="9999999999",
        password=DEFAULT_SEED_PASSWORD,
    )

    # Managers per service unit
    managers = [
        ("Electrical Unit", "Electrical Manager", "manager.electrical@cdgi.edu.in"),
        ("Plumbing Unit", "Plumbing Manager", "manager.plumbing@cdgi.edu.in"),
        ("IT Support Unit", "IT Manager", "manager.it@cdgi.edu.in"),
        ("Hygiene Unit", "Hygiene Manager", "manager.hygiene@cdgi.edu.in"),
        ("Transport Unit", "Transport Manager", "manager.transport@cdgi.edu.in"),
    ]
    for unit_name, mgr_name, mgr_email in managers:
        unit = ServiceUnit.query.filter_by(name=unit_name).first()
        if not unit:
            unit = ServiceUnit(name=unit_name)
            db.session.add(unit)
            db.session.commit()
        mgr = upsert_user(
            email=mgr_email,
            name=mgr_name,
            role="service_unit_manager",
            dept="Administration",
            service_unit_id=unit.id,
            password=DEFAULT_SEED_PASSWORD,
        )
        unit.manager_id = mgr.id
        db.session.commit()

    # Staff per service unit (for assignment testing)
    staff_users = [
        ("Electrical Unit", "Electrical Staff", "staff.electrical@cdgi.edu.in"),
        ("Plumbing Unit", "Plumbing Staff", "staff.plumbing@cdgi.edu.in"),
        ("IT Support Unit", "IT Staff", "staff.it@cdgi.edu.in"),
        ("Hygiene Unit", "Hygiene Staff", "staff.hygiene@cdgi.edu.in"),
        ("Transport Unit", "Transport Staff", "staff.transport@cdgi.edu.in"),
    ]
    for unit_name, staff_name, staff_email in staff_users:
        unit = ServiceUnit.query.filter_by(name=unit_name).first()
        if unit:
            upsert_user(
                email=staff_email,
                name=staff_name,
                role="staff",
                dept="Administration",
                service_unit_id=unit.id,
                password=DEFAULT_SEED_PASSWORD,
            )

with app.app_context():
    try:
        db.create_all()
        run_migrations()
        # Create service units if they don't exist
        service_units_data = [
            "Electrical Unit",
            "Plumbing Unit",
            "IT Support Unit",
            "Hygiene Unit",
            "Transport Unit"
        ]
        for unit_name in service_units_data:
            if not ServiceUnit.query.filter_by(name=unit_name).first():
                db.session.add(ServiceUnit(name=unit_name))
        db.session.commit()
        # Seed default users (managers, staff, hods, principal, demo student)
        seed_default_accounts()
        # Create categories if they don't exist - ONLY for units with managers
        categories_data = [
            ("Electrical Fault", "Electrical Unit"),
            ("Power Issue", "Electrical Unit"),
            ("Lighting Problem", "Electrical Unit"),
            ("Pipe Leakage", "Plumbing Unit"),
            ("Water Supply Issue", "Plumbing Unit"),
            ("Drainage Problem", "Plumbing Unit"),
            ("Internet/WiFi Issue", "IT Support Unit"),
            ("Network Problem", "IT Support Unit"),
            ("Software Issue", "IT Support Unit"),
            ("Hardware Repair", "IT Support Unit"),
            ("Cleanliness", "Hygiene Unit"),
            ("Waste Management", "Hygiene Unit"),
            ("Sanitation Issue", "Hygiene Unit"),
            ("Vehicle Issue", "Transport Unit"),
            ("Route Problem", "Transport Unit"),
            ("Bus/Transport Service", "Transport Unit")
        ]
        for cat_name, unit_name in categories_data:
            if not Category.query.filter_by(name=cat_name).first():
                unit = ServiceUnit.query.filter_by(name=unit_name).first()
                if unit:
                    db.session.add(Category(name=cat_name, service_unit_id=unit.id))
        db.session.commit()
        backfill_complaint_routing()
        run_pending_escalations()
    except Exception as e:
        print(f"Startup error: {e}")

if __name__=="__main__":
    PORT = int(os.environ.get('PORT', 5002))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print("="*50); print(f"  | http://localhost:{PORT}")
    print(f"  Gmail API: {'ready' if os.path.exists(TOKEN_FILE) else 'run setup_gmail.py'}")
    print(f"  SMTP: {'ready' if SMTP_OK else 'not set'}"); print("="*50)
    app.run(debug=DEBUG,port=PORT,host="0.0.0.0")
