"""
CIRS v4 — Gmail API + Email Verify + Before/After Photos
CDGI Indore 2025-26
"""
import os, re, base64, json, secrets, smtplib
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
CREDS_FILE = os.path.join(BASE_DIR, "credentials.json")
APP_URL    = os.getenv("APP_URL", "http://localhost:5000")
RENDER_ENV = os.getenv("RENDER", "").lower() == "true" or bool(os.getenv("RENDER_EXTERNAL_URL"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()
if RENDER_EXTERNAL_URL:
    APP_URL = RENDER_EXTERNAL_URL.rstrip("/")

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

DB_HOST=os.getenv("DB_HOST","localhost"); DB_NAME=os.getenv("DB_NAME","postgres")
DB_USER=os.getenv("DB_USER","postgres"); DB_PASSWORD=os.getenv("DB_PASSWORD","password")
DB_PORT=os.getenv("DB_PORT","5432")
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args":{"sslmode":"require"},"pool_pre_ping":True,"pool_recycle":300}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET","CIRS_CDGI_V4_SECRET")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 32*1024*1024

ALLOWED_EXT = {"png","jpg","jpeg","gif","mp4","pdf"}
SMTP_HOST=os.getenv("SMTP_HOST","smtp.gmail.com").strip(); SMTP_PORT=int(os.getenv("SMTP_PORT","587"))
SMTP_USER=os.getenv("SMTP_USER","").strip(); SMTP_PASS=os.getenv("SMTP_PASS","").replace(" ","").strip()
EMAIL_FROM=os.getenv("EMAIL_FROM",SMTP_USER).strip() or SMTP_USER; SMTP_OK=bool(SMTP_USER and SMTP_PASS)
EMAIL_VERIFY_ENABLED=os.getenv("EMAIL_VERIFY_ENABLED","false").lower()=="true"
MAIL_MODE=os.getenv("MAIL_MODE","smtp" if RENDER_ENV else "auto").lower().strip()
PHOTO_VIEW_ROLES={"admin","faculty","coordinator"}

db=SQLAlchemy(app); jwt=JWTManager(app); os.makedirs(UPLOAD_DIR,exist_ok=True)

# MODELS
class User(db.Model):
    __tablename__="users"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(150),nullable=False)
    email=db.Column(db.String(150),unique=True,nullable=False)
    password=db.Column(db.String(255),nullable=False)
    role=db.Column(db.String(30),default="student")
    dept=db.Column(db.String(100),default="CSE")
    roll_no=db.Column(db.String(50)); phone=db.Column(db.String(20))
    is_verified=db.Column(db.Boolean,default=False)
    verify_token=db.Column(db.String(100)); verify_expires=db.Column(db.DateTime)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    complaints=db.relationship("Complaint",backref="reporter",lazy=True,foreign_keys="Complaint.user_id")
    def to_dict(self):
        return {"id":self.id,"name":self.name,"email":self.email,"role":self.role,"dept":self.dept,
                "roll_no":self.roll_no or "","phone":self.phone or "","is_verified":self.is_verified,
                "created_at":self.created_at.strftime("%Y-%m-%d")}

class Complaint(db.Model):
    __tablename__="complaints"
    id=db.Column(db.Integer,primary_key=True)
    ticket_id=db.Column(db.String(20),unique=True,nullable=False)
    title=db.Column(db.String(250),nullable=False)
    category=db.Column(db.String(50),nullable=False)
    description=db.Column(db.Text,nullable=False)
    priority=db.Column(db.String(20),default="medium")
    status=db.Column(db.String(30),default="new")
    location=db.Column(db.String(200))
    image_before=db.Column(db.String(300))   # student uploads when reporting
    image_after=db.Column(db.String(300))    # staff uploads when resolving
    dept=db.Column(db.String(100)); assigned_to=db.Column(db.String(150))
    resolved_by=db.Column(db.String(150)); feedback=db.Column(db.Integer)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    def to_dict(self, viewer=None):
        can_view_student_photo = bool(viewer and getattr(viewer, "role", "") in PHOTO_VIEW_ROLES)
        return {"id":self.id,"ticket_id":self.ticket_id,"title":self.title,"category":self.category,
                "description":self.description,"priority":self.priority,"status":self.status,
                "location":self.location or "",
                "image_before":f"{APP_URL}{self.image_before}" if (self.image_before and can_view_student_photo) else None,
                "image_after":f"{APP_URL}{self.image_after}" if self.image_after else None,
                "dept":self.dept or "","assigned_to":self.assigned_to or "",
                "resolved_by":self.resolved_by or "","feedback":self.feedback,
                "user_id":self.user_id,
                "user_name":self.reporter.name if self.reporter else "",
                "user_email":self.reporter.email if self.reporter else "",
                "user_dept":self.reporter.dept if self.reporter else "",
                "user_roll":self.reporter.roll_no if self.reporter else "",
                "user_phone":self.reporter.phone if self.reporter else "",
                "can_view_student_photo":can_view_student_photo,
                "created_at":self.created_at.strftime("%Y-%m-%d"),
                "updated_at":self.updated_at.strftime("%Y-%m-%d") if self.updated_at else ""}

class Notification(db.Model):
    __tablename__="notifications"
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    message=db.Column(db.Text,nullable=False); is_read=db.Column(db.Boolean,default=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    def to_dict(self):
        return {"id":self.id,"message":self.message,"is_read":self.is_read,"created_at":self.created_at.strftime("%Y-%m-%d %H:%M")}

# HELPERS
CAT_DEPT={"hygiene":"Maintenance","electrical":"Electrical","transport":"Transport","maintenance":"Maintenance","safety":"Security","admin":"Administration","water":"Maintenance"}
VALID_PRI={"low","medium","high"}; VALID_STA={"new","in-progress","resolved"}
CAN_VIEW=("admin","coordinator","faculty"); CAN_MNG=("admin","coordinator","faculty")

def gen_ticket(): return f"TKT-{str(Complaint.query.count()+1).zfill(4)}"
def allowed_file(f): return ".." not in f and f.rsplit(".",1)[-1].lower() in ALLOWED_EXT
def val_phone(p): return bool(re.fullmatch(r"\d{10}",p)) if p else True
def push_notif(uid,msg):
    try: db.session.add(Notification(user_id=uid,message=msg)); db.session.commit()
    except: pass
def save_upload(file,prefix=""):
    if file and file.filename and allowed_file(file.filename):
        fname=f"{prefix}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"],fname))
        return f"/uploads/{fname}"
    return None

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
    except: return None

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
            print(f"[GMAIL OK] {to}")
            return True, "gmail_api", ""
        except Exception as e:
            print(f"[GMAIL FAIL] {e}")
            gmail_err=str(e)
    else:
        gmail_err="gmail_token.json missing or Gmail API unavailable"
    if SMTP_OK:
        try:
            with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=20) as s:
                s.ehlo()
                s.starttls()
                s.login(SMTP_USER,SMTP_PASS)
                s.sendmail(EMAIL_FROM,[to],msg.as_string())
            print(f"[SMTP OK] {to}")
            return True, "smtp", ""
        except Exception as e:
            print(f"[SMTP FAIL] {e}")
            return False, "smtp", str(e)
    print(f"[EMAIL SKIP] {to}: {subj}")
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
    body=f"""<div style="background:#dbeafe;border:1px solid #93c5fd;border-radius:8px;padding:12px;margin-bottom:16px;"><p style="margin:0;color:#1e40af;font-weight:700;">✅ Complaint Received — Under Process</p></div>
<p>Dear <strong>{name}</strong>, your complaint is <strong>under process</strong>.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:13px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
<tr style="background:#1a4faa;color:#fff;"><td style="padding:9px 12px;font-weight:700;" colspan="2">Complaint Details</td></tr>
<tr style="background:#f8fafc;"><td style="padding:8px 12px;color:#6b7280;width:35%;">Ticket ID</td><td style="padding:8px 12px;font-weight:700;color:#1a4faa;">{tid}</td></tr>
<tr><td style="padding:8px 12px;color:#6b7280;">Title</td><td style="padding:8px 12px;">{title}</td></tr>
<tr style="background:#f8fafc;"><td style="padding:8px 12px;color:#6b7280;">Category</td><td style="padding:8px 12px;">{cat.capitalize()}</td></tr>
<tr><td style="padding:8px 12px;color:#6b7280;">Status</td><td style="padding:8px 12px;"><span style="background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700;">⏳ Under Process</span></td></tr>
</table>
<p style="background:#f8fafc;padding:10px;border-radius:8px;border-left:3px solid #1a4faa;font-size:13px;">Save your Ticket ID <strong style="color:#1a4faa;">{tid}</strong>. You'll get another email when resolved.</p>"""
    return tpl_base("linear-gradient(135deg,#1a4faa,#b91c1c)","CDGI Campus Issues Portal",body)

def email_resolved(name,tid,title,by,after_url=""):
    img=""
    if after_url: img=f'''
    <div style="margin:14px 0;">
    <p style="color:#6b7280;font-size:12px;font-weight:700;">📸 After Resolution Photo:</p><img src="{after_url}" style="max-width:100%;border-radius:8px;border:2px solid #bbf7d0;" alt="Resolved"/></div>'''
    body=f"""<div style="background:#dcfce7;border:1px solid #86efac;border-radius:8px;padding:12px;margin-bottom:16px;"><p style="margin:0;color:#166534;font-weight:700;">🎉 Your issue has been resolved!</p></div>
<p>Dear <strong>{name}</strong>, your campus issue has been <strong>successfully resolved</strong>.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:13px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
<tr style="background:#166534;color:#fff;"><td style="padding:9px 12px;font-weight:700;" colspan="2">Resolution Details</td></tr>
<tr style="background:#f8fafc;"><td style="padding:8px 12px;color:#6b7280;width:35%;">Ticket ID</td><td style="padding:8px 12px;font-weight:700;color:#166534;">{tid}</td></tr>
<tr><td style="padding:8px 12px;color:#6b7280;">Issue</td><td style="padding:8px 12px;">{title}</td></tr>
<tr style="background:#f8fafc;"><td style="padding:8px 12px;color:#6b7280;">Resolved By</td><td style="padding:8px 12px;">{by or "CDGI Staff"}</td></tr>
<tr><td style="padding:8px 12px;color:#6b7280;">Status</td><td style="padding:8px 12px;"><span style="background:#dcfce7;color:#166534;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:700;"> Resolved</span></td></tr>
</table>{img}
<p style="background:#f0fdf4;padding:10px;border-radius:8px;border-left:3px solid #166534;font-size:13px;">Please log in to <strong>rate the resolution</strong>. Your feedback helps improve campus services.</p>"""
    return tpl_base("linear-gradient(135deg,#166534,#15803d)","Issue Successfully Resolved!",body)

# ROUTES
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
    return """<html><head><meta http-equiv="refresh" content="3;url=/"></head>
    <body style="font-family:Arial;text-align:center;padding:60px;background:#f0fdf4;">
    <div style="font-size:60px;">✅</div><h2 style="color:#166534;">Email Verified!</h2>
    <p>Redirecting to login in 3 seconds…</p></body></html>"""

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

@app.route("/api/complaints",methods=["GET"])
@jwt_required()
def get_complaints():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user: return jsonify({"error":"Not found"}),404
    q=Complaint.query if user.role in CAN_VIEW else Complaint.query.filter_by(user_id=uid)
    st=request.args.get("status"); cat=request.args.get("category"); srch=request.args.get("search")
    if st: q=q.filter_by(status=st)
    if cat: q=q.filter_by(category=cat)
    if srch: q=q.filter(db.or_(Complaint.title.ilike(f"%{srch}%"),Complaint.ticket_id.ilike(f"%{srch}%")))
    complaints=q.order_by(Complaint.created_at.desc()).all()
    return jsonify({"status":"success","data":[c.to_dict(user) for c in complaints],"count":len(complaints)})

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
    img_before=save_upload(request.files.get("image"),prefix="before") if "image" in request.files else None
    tid=gen_ticket()
    c=Complaint(ticket_id=tid,title=title,category=category,description=desc,priority=priority,
                location=location,dept=CAT_DEPT.get(category,"General"),image_before=img_before,user_id=uid)
    db.session.add(c)
    for u in User.query.filter(User.role.in_(["admin","coordinator","faculty"])).all():
        push_notif(u.id,f"New complaint {tid}: {title} — by {user.name}")
    db.session.commit()
    sent, provider, err = send_email(user.email,f"✅ Complaint {tid} Received | CDGI CIRS",email_received(user.name,tid,title,category))
    msg=f"Complaint {tid} submitted."
    if sent: msg+=f" Confirmation email sent via {provider}."
    else: msg+=f" Saved successfully, but confirmation email failed: {err or 'mail service unavailable'}."
    return jsonify({"status":"success","message":msg,"email_sent":sent,"complaint":c.to_dict(user)}),201

@app.route("/api/complaints/<ticket_id>",methods=["GET"])
@jwt_required()
def get_complaint(ticket_id):
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    c=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}),404
    if user.role not in CAN_VIEW and c.user_id!=uid: return jsonify({"error":"Unauthorized"}),403
    return jsonify(c.to_dict(user))

@app.route("/api/complaints/<ticket_id>",methods=["PUT"])
@jwt_required()
def update_complaint(ticket_id):
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    c=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}),404
    if user.role in CAN_MNG:
        data=request.get_json() or {}; old=c.status
        if "status" in data:
            if data["status"] not in VALID_STA: return jsonify({"error":"Invalid status"}),400
            c.status=data["status"]
        if "priority" in data and user.role in ("admin","coordinator"):
            if data["priority"] not in VALID_PRI: return jsonify({"error":"Invalid priority"}),400
            c.priority=data["priority"]
        if "assigned_to" in data: c.assigned_to=data["assigned_to"]
        if "resolved_by" in data: c.resolved_by=data["resolved_by"]
        c.updated_at=datetime.utcnow(); db.session.commit()
        reporter=db.session.get(User,c.user_id)
        mail_msg=""
        if reporter and c.status!=old:
            if c.status=="resolved":
                after_url=f"{APP_URL}{c.image_after}" if c.image_after else ""
                sent, provider, err = send_email(reporter.email,f"✅ Issue Resolved — {ticket_id} | CDGI CIRS",
                           email_resolved(reporter.name,ticket_id,c.title,c.resolved_by or user.name,after_url))
            else:
                sent, provider, err = send_email(reporter.email,f"📢 Complaint Update — {ticket_id}",
                           f"<p>Dear {reporter.name}, complaint {ticket_id} is now <strong>{c.status}</strong>.</p>")
            mail_msg=f" Email sent via {provider}." if sent else f" Email failed: {err or 'mail service unavailable'}."
        push_notif(c.user_id,f"Complaint {ticket_id} → {c.status}")
        return jsonify({"status":"success","message":f"Complaint {ticket_id} updated to {c.status}.{mail_msg}","complaint":c.to_dict(user)})
    data=request.get_json() or {}
    if "feedback" in data and c.user_id==uid and c.status=="resolved":
        r=int(data["feedback"])
        if not 1<=r<=5: return jsonify({"error":"Rating 1-5"}),400
        c.feedback=r; db.session.commit()
        return jsonify({"status":"success","message":"Feedback submitted!"})
    return jsonify({"error":"Unauthorized"}),403

@app.route("/api/complaints/<ticket_id>/after-photo",methods=["POST"])
@jwt_required()
def upload_after_photo(ticket_id):
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user or user.role not in CAN_MNG: return jsonify({"error":"Unauthorized"}),403
    c=Complaint.query.filter_by(ticket_id=ticket_id).first()
    if not c: return jsonify({"error":"Not found"}),404
    if "image_after" not in request.files: return jsonify({"error":"No image"}),400
    img=save_upload(request.files["image_after"],prefix=f"after_{ticket_id}")
    if not img: return jsonify({"error":"Invalid file"}),400
    c.image_after=img; c.resolved_by=user.name; c.status="resolved"; c.updated_at=datetime.utcnow()
    db.session.commit()
    reporter=db.session.get(User,c.user_id)
    sent=False; provider=""; err=""
    if reporter:
        sent, provider, err = send_email(reporter.email,f"✅ Issue Resolved — {ticket_id} | CDGI CIRS",
                   email_resolved(reporter.name,ticket_id,c.title,user.name,f"{APP_URL}{img}"))
    push_notif(c.user_id,f"✅ {ticket_id} resolved by {user.name}")
    msg="Resolution photo uploaded and complaint marked resolved."
    if reporter:
        msg += f" Email sent via {provider}." if sent else f" Email failed: {err or 'mail service unavailable'}."
    return jsonify({"status":"success","message":msg,"complaint":c.to_dict(user)})

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
            except: pass
    db.session.delete(c); db.session.commit()
    return jsonify({"status":"success","message":f"{ticket_id} deleted"})

@app.route("/api/stats",methods=["GET"])
@jwt_required()
def get_stats():
    uid=int(get_jwt_identity()); user=db.session.get(User,uid)
    if not user: return jsonify({"error":"Not found"}),404
    base=Complaint.query if user.role in CAN_VIEW else Complaint.query.filter_by(user_id=uid)
    total=base.count(); new_c=base.filter_by(status="new").count()
    inp=base.filter_by(status="in-progress").count(); res=base.filter_by(status="resolved").count()
    cats={}
    for c in base.all(): cats[c.category]=cats.get(c.category,0)+1
    return jsonify({"total":total,"new":new_c,"in_progress":inp,"resolved":res,"categories":cats,
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

with app.app_context():
    try:
        db.create_all(); print("✅ DB ready")
        if not User.query.filter_by(role="admin").first():
            db.session.add(User(name="Admin CDGI",email="admin@cdgi.edu.in",
                password=generate_password_hash("admin123"),role="admin",dept="CSE",
                roll_no="ADMIN001",phone="0000000000",is_verified=True))
            db.session.commit(); print("✅ Admin: admin@cdgi.edu.in / admin123")
    except Exception as e: print(f"❌ {e}")

if __name__=="__main__":
    print("━"*50); print(f"  🏛️  CIRS v4 | http://localhost:5000")
    print(f"  📧  Gmail API: {'✅' if os.path.exists(TOKEN_FILE) else '⚠️  Run setup_gmail.py'}")
    print(f"  📧  SMTP: {'✅' if SMTP_OK else '⚠️  Not set'}"); print("━"*50)
    app.run(debug=True,port=5000,host="0.0.0.0")
