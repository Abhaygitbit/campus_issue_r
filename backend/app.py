"""
CIRS v5 — Staff Assignment Workflow + Multi Image Support
CDGI Indore 2025-26
"""
import os, re, base64, secrets, smtplib
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory
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
MAIL_MODE=os.getenv("MAIL_MODE","smtp" if RENDER_ENV else "auto").lower().strip()
MANAGE_ROLES={"admin","faculty","coordinator"}
ASSIGN_ROLES={"admin","faculty","coordinator"}
PHOTO_ALL_ROLES={"admin","faculty","coordinator"}

os.makedirs(UPLOAD_DIR,exist_ok=True)
db=SQLAlchemy(app)
jwt=JWTManager(app)

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
    complaints=db.relationship("Complaint",backref="reporter",lazy=True,foreign_keys="Complaint.user_id")
    assigned_complaints=db.relationship("Complaint",backref="assigned_staff",lazy=True,foreign_keys="Complaint.assigned_staff_id")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"email":self.email,"role":self.role,"dept":self.dept,
                "roll_no":self.roll_no or "","phone":self.phone or "","is_verified":self.is_verified,
                "created_at":self.created_at.strftime("%Y-%m-%d") if self.created_at else ""}

class Complaint(db.Model):
    __tablename__="complaints"
    id=db.Column(db.Integer,primary_key=True)
    ticket_id=db.Column(db.String(20),unique=True,nullable=False)
    title=db.Column(db.String(250),nullable=False)
    category=db.Column(db.String(50),nullable=False)
    description=db.Column(db.Text,nullable=False)
    priority=db.Column(db.String(20),default="medium")
    status=db.Column(db.String(30),default="pending-assignment")
    location=db.Column(db.String(200))
    image_before=db.Column(db.String(300))
    image_after=db.Column(db.String(300))
    dept=db.Column(db.String(100))
    assigned_to=db.Column(db.String(150))
    assigned_staff_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=True)
    resolved_by=db.Column(db.String(150))
    feedback=db.Column(db.Integer)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)

    def normalize_status(self):
        mapping = {"new":"pending-assignment"}
        if self.status in mapping:
            self.status = mapping[self.status]

    def _can_view_student_images(self, viewer):
        if not viewer:
            return False
        if viewer.role in PHOTO_ALL_ROLES:
            return True
        if viewer.id == self.user_id:
            return True
        if viewer.role == "staff" and self.assigned_staff_id == viewer.id:
            return True
        return False

    def _can_view_resolution_images(self, viewer):
        if not viewer:
            return False
        if viewer.role in PHOTO_ALL_ROLES:
            return True
        if viewer.id == self.user_id:
            return True
        if viewer.role == "staff" and self.assigned_staff_id == viewer.id:
            return True
        return False

    def to_dict(self, viewer=None):
        self.normalize_status()
        can_view_student_images = self._can_view_student_images(viewer)
        can_view_resolution_images = self._can_view_resolution_images(viewer)
        issue_images = [img.to_dict() for img in self.issue_images.order_by(IssueImage.created_at.asc()).all()] if can_view_student_images else []
        resolution_images = [img.to_dict() for img in self.resolution_images.order_by(ResolutionImage.created_at.asc()).all()] if can_view_resolution_images else []
        if self.image_before and can_view_student_images and not issue_images:
            issue_images.append({"id": f"legacy_before_{self.id}", "image_url": f"{APP_URL}{self.image_before}", "uploaded_by": "student", "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""})
        if self.image_after and can_view_resolution_images and not resolution_images:
            resolution_images.append({"id": f"legacy_after_{self.id}", "image_url": f"{APP_URL}{self.image_after}", "uploaded_by": self.resolved_by or "staff", "created_at": self.updated_at.strftime("%Y-%m-%d %H:%M") if self.updated_at else ""})
        return {
            "id":self.id,"ticket_id":self.ticket_id,"title":self.title,"category":self.category,
            "description":self.description,"priority":self.priority,"status":self.status,
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
            "user_roll":self.reporter.roll_no if self.reporter else "",
            "user_phone":self.reporter.phone if self.reporter else "",
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
        return {"id": self.id, "image_url": f"{APP_URL}{self.image_path}", "uploaded_by": self.uploaded_by, "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""}

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
        return {"id": self.id, "image_url": f"{APP_URL}{self.image_path}", "uploaded_by": self.staff.name if self.staff else "staff", "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else ""}

class Notification(db.Model):
    __tablename__="notifications"
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    message=db.Column(db.Text,nullable=False)
    is_read=db.Column(db.Boolean,default=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    def to_dict(self):
        return {"id":self.id,"message":self.message,"is_read":self.is_read,"created_at":self.created_at.strftime("%Y-%m-%d %H:%M")}

CAT_DEPT={"hygiene":"Maintenance","electrical":"Electrical","transport":"Transport","maintenance":"Maintenance","safety":"Security","admin":"Administration","water":"Maintenance"}
VALID_PRI={"low","medium","high"}
VALID_STA={"pending-assignment","assigned","in-progress","resolved"}


def gen_ticket():
    return f"TKT-{str((db.session.query(db.func.count(Complaint.id)).scalar() or 0)+1).zfill(4)}"

def allowed_file(filename, image_only=False):
    if not filename or ".." in filename or "." not in filename:
        return False
    ext = filename.rsplit(".",1)[-1].lower()
    return ext in (IMAGE_EXT if image_only else ALLOWED_EXT)

def val_phone(p): return bool(re.fullmatch(r"\d{10}",p)) if p else True

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

def complaint_query_for_user(user):
    if user.role in MANAGE_ROLES:
        return Complaint.query
    if user.role == "staff":
        return Complaint.query.filter_by(assigned_staff_id=user.id)
    return Complaint.query.filter_by(user_id=user.id)

def can_access_complaint(user, complaint):
    if user.role in MANAGE_ROLES:
        return True
    if user.role == "staff":
        return complaint.assigned_staff_id == user.id
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

def email_received(name,tid,title,cat):
    body=f"<p>Dear <strong>{name}</strong>, your complaint is now in the queue for faculty assignment.</p><p><strong>Ticket:</strong> {tid}<br><strong>Issue:</strong> {title}<br><strong>Category:</strong> {cat.capitalize()}<br><strong>Status:</strong> Pending Assignment</p>"
    return tpl_base("linear-gradient(135deg,#1a4faa,#b91c1c)","Complaint Received",body)

def email_assigned(staff_name, ticket_id, title):
    body=f"<p>Dear <strong>{staff_name}</strong>, a new issue has been assigned to you.</p><p><strong>Ticket:</strong> {ticket_id}<br><strong>Issue:</strong> {title}<br><strong>Status:</strong> Assigned</p><p>Please log in and update the progress.</p>"
    return tpl_base("linear-gradient(135deg,#7c3aed,#2563eb)","New Issue Assigned",body)

def email_resolved(name,tid,title,by,after_urls=None):
    imgs = "".join([f'<img src="{u}" style="max-width:100%;border-radius:8px;border:2px solid #bbf7d0;margin-top:8px;" alt="Resolved"/>' for u in (after_urls or [])[:3]])
    body=f"<p>Dear <strong>{name}</strong>, your issue has been resolved.</p><p><strong>Ticket:</strong> {tid}<br><strong>Issue:</strong> {title}<br><strong>Resolved By:</strong> {by}</p>{imgs}<p>Please log in to verify and rate the resolution.</p>"
    return tpl_base("linear-gradient(135deg,#166534,#15803d)","Issue Successfully Resolved!",body)

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
    vtok=secrets.token_urlsafe(32); vexp=datetime.utcnow()+timedelta(hours=24)
    user=User(name=data["name"].strip(),email=email,password=generate_password_hash(data["password"]),
              role=data.get("role","student"),dept=data.get("dept","CSE"),roll_no=data.get("roll_no",""),phone=phone,
              is_verified=not EMAIL_VERIFY_ENABLED,
              verify_token=vtok if EMAIL_VERIFY_ENABLED else None,
              verify_expires=vexp if EMAIL_VERIFY_ENABLED else None)
    db.session.add(user); db.session.commit()
    if EMAIL_VERIFY_ENABLED:
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
    db.session.commit(); return jsonify({"status":"success","user":user.to_dict()})

@app.route("/api/staff/options", methods=["GET"])
@jwt_required()
def get_staff_options():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role not in ASSIGN_ROLES:
        return jsonify({"error": "Access denied"}), 403
    staff = User.query.filter_by(role="staff").order_by(User.name.asc()).all()
    return jsonify({"status":"success", "data":[s.to_dict() for s in staff]})

@app.route("/api/complaints",methods=["GET"])
@jwt_required()
def get_complaints():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user: return jsonify({"error":"Not found"}),404
    q=complaint_query_for_user(user)
    st=request.args.get("status"); cat=request.args.get("category"); srch=request.args.get("search")
    if st: q=q.filter_by(status=st)
    if cat: q=q.filter_by(category=cat)
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
    title=request.form.get("title","").strip(); category=request.form.get("category","").strip()
    desc=request.form.get("description","").strip(); location=request.form.get("location","").strip()
    if not title or not category or not desc: return jsonify({"error":"Title, category, description required"}),400
    if category not in CAT_DEPT: return jsonify({"error":"Invalid category"}),400
    priority="medium"
    if user.role in ("admin","coordinator"):
        p=request.form.get("priority","medium")
        if p in VALID_PRI: priority=p
    c=Complaint(ticket_id=gen_ticket(),title=title,category=category,description=desc,priority=priority,
                location=location,dept=CAT_DEPT.get(category,"General"),user_id=uid,status="pending-assignment")
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
            db.session.add(IssueImage(complaint_id=c.id, image_path=saved, uploaded_by="student"))
    if uploaded:
        c.image_before = uploaded[0]
    db.session.commit()
    for u in User.query.filter(User.role.in_(["admin","coordinator","faculty"])).all():
        push_notif(u.id,f"New complaint {c.ticket_id}: {title} — pending assignment")
    sent, provider, err = send_email(user.email,f"✅ Complaint {c.ticket_id} Received | CDGI CIRS",email_received(user.name,c.ticket_id,title,category))
    msg=f"Complaint {c.ticket_id} submitted."
    if sent: msg+=f" Confirmation email sent via {provider}."
    else: msg+=f" Saved successfully, but confirmation email failed: {err or 'mail service unavailable'}."
    return jsonify({"status":"success","message":msg,"email_sent":sent,"complaint":c.to_dict(user)}),201

@app.route("/api/complaints/<ticket_id>",methods=["GET"])
@jwt_required()
def get_complaint(ticket_id):
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    c=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}),404
    if not can_access_complaint(user, c): return jsonify({"error":"Unauthorized"}),403
    return jsonify(c.to_dict(user))

@app.route("/api/complaints/<ticket_id>/assign", methods=["POST"])
@jwt_required()
def assign_complaint(ticket_id):
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or user.role not in ASSIGN_ROLES:
        return jsonify({"error":"Only faculty/admin/coordinator can assign issues"}), 403
    complaint = Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not complaint:
        return jsonify({"error":"Not found"}), 404
    data = request.get_json() or {}
    staff_id = data.get("assigned_staff_id")
    if not staff_id:
        return jsonify({"error":"assigned_staff_id required"}), 400
    staff = db.session.get(User, int(staff_id))
    if not staff or staff.role != "staff":
        return jsonify({"error":"Selected user is not a valid staff member"}), 400
    complaint.assigned_staff_id = staff.id
    complaint.assigned_to = staff.name
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
    data=request.get_json() or {}
    old=c.status
    if user.role in MANAGE_ROLES or (user.role == "staff" and c.assigned_staff_id == user.id):
        if "status" in data:
            if data["status"] not in VALID_STA: return jsonify({"error":"Invalid status"}),400
            if user.role == "staff" and data["status"] not in {"assigned", "in-progress", "resolved"}:
                return jsonify({"error":"Staff cannot set this status"}),400
            if user.role == "staff" and not c.assigned_staff_id == user.id:
                return jsonify({"error":"Unauthorized"}),403
            c.status=data["status"]
        if user.role in ("admin","coordinator") and "priority" in data:
            if data["priority"] not in VALID_PRI: return jsonify({"error":"Invalid priority"}),400
            c.priority=data["priority"]
        if user.role in MANAGE_ROLES and "assigned_to" in data:
            c.assigned_to=data["assigned_to"]
        if user.role in MANAGE_ROLES and "resolved_by" in data:
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
    if "feedback" in data and c.user_id==uid and c.status=="resolved":
        r=int(data["feedback"])
        if not 1<=r<=5: return jsonify({"error":"Rating 1-5"}),400
        c.feedback=r; db.session.commit()
        return jsonify({"status":"success","message":"Feedback submitted!"})
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
    if user.role == "staff":
        if complaint.assigned_staff_id != user.id:
            return jsonify({"error":"Unauthorized"}),403
    elif user.role not in MANAGE_ROLES:
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
        urls = [f"{APP_URL}{path}" for path in added]
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
    base=complaint_query_for_user(user)
    total=base.count(); pending=base.filter_by(status="pending-assignment").count()
    assigned=base.filter_by(status="assigned").count()
    inp=base.filter_by(status="in-progress").count(); res=base.filter_by(status="resolved").count()
    cats={}
    for c in base.all(): cats[c.category]=cats.get(c.category,0)+1
    return jsonify({"total":total,"pending_assignment":pending,"assigned":assigned,"new":pending,
                    "in_progress":inp,"resolved":res,"categories":cats,
                    "total_users":User.query.count() if user.role=="admin" else None,
                    "resolution_rate":round((res/total*100) if total else 0,1)})

@app.route("/api/users",methods=["GET"])
@jwt_required()
def get_users():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user or user.role not in ("admin","coordinator","faculty"): return jsonify({"error":"Access denied"}),403
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
    dialect = db.engine.dialect.name
    stmts = []
    if 'assigned_staff_id' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN assigned_staff_id INTEGER')
    if 'image_before' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN image_before VARCHAR(300)')
    if 'image_after' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN image_after VARCHAR(300)')
    if 'resolved_by' not in cols:
        stmts.append('ALTER TABLE complaints ADD COLUMN resolved_by VARCHAR(150)')
    if 'is_verified' not in {c['name'] for c in inspector.get_columns('users')}:
        stmts.append('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1')
    if 'verify_token' not in {c['name'] for c in inspector.get_columns('users')}:
        stmts.append('ALTER TABLE users ADD COLUMN verify_token VARCHAR(100)')
    if 'verify_expires' not in {c['name'] for c in inspector.get_columns('users')}:
        stmts.append('ALTER TABLE users ADD COLUMN verify_expires DATETIME')
    for stmt in stmts:
        try:
            db.session.execute(db.text(stmt))
            db.session.commit()
        except Exception:
            db.session.rollback()
    # data backfill
    try:
        db.session.execute(db.text("UPDATE complaints SET status='pending-assignment' WHERE status='new' OR status IS NULL"))
        db.session.commit()
    except Exception:
        db.session.rollback()

with app.app_context():
    try:
        db.create_all()
        run_migrations()
        if not User.query.filter_by(role="admin").first():
            db.session.add(User(name="Admin CDGI",email="admin@cdgi.edu.in", password=generate_password_hash("admin123"),role="admin",dept="CSE", roll_no="ADMIN001",phone="0000000000",is_verified=True))
            db.session.commit()
    except Exception as e:
        print(f"❌ {e}")

if __name__=="__main__":
    PORT = int(os.environ.get('PORT', 5002))
    print("━"*50); print(f"  🏛️  CIRS v5 | http://localhost:{PORT}")
    print(f"  📧  Gmail API: {'✅' if os.path.exists(TOKEN_FILE) else '⚠️  Run setup_gmail.py'}")
    print(f"  📧  SMTP: {'✅' if SMTP_OK else '⚠️  Not set'}"); print("━"*50)
    app.run(debug=True,port=PORT,host="0.0.0.0")
