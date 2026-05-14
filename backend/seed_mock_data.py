import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import app, db, User, Complaint, ServiceUnit, Category, IssueImage

def seed_data():
    with app.app_context():
        # 1. Clear existing data (Optional, but good for clean testing)
        # db.drop_all()
        # db.create_all()

        # 2. Create Principal
        principal_email = "principal@cdgi.edu.in"
        if not User.query.filter_by(email=principal_email).first():
            principal = User(
                name="Principal CDGI",
                email=principal_email,
                password=generate_password_hash("Principal@123"),
                role="principal",
                dept="Administration",
                is_verified=True
            )
            db.session.add(principal)
            print("Principal created.")

        # 3. Create Service Units
        units = ["Maintenance", "Electrical", "IT Support", "Security"]
        for u_name in units:
            if not ServiceUnit.query.filter_by(name=u_name).first():
                unit = ServiceUnit(name=u_name)
                db.session.add(unit)
        db.session.commit()

        # 4. Create categories
        categories = [
            ("Plumbing Issue", "Maintenance"),
            ("Fan Not Working", "Electrical"),
            ("Internet Down", "IT Support"),
            ("CCTV Camera Repair", "Security"),
            ("Cleaning Required", "Maintenance")
        ]
        for cat_name, unit_name in categories:
            unit = ServiceUnit.query.filter_by(name=unit_name).first()
            if unit and not Category.query.filter_by(name=cat_name).first():
                cat = Category(name=cat_name, service_unit_id=unit.id)
                db.session.add(cat)
        db.session.commit()

        # 5. Create a Service Unit Manager
        manager_email = "manager@cdgi.edu.in"
        m_unit = ServiceUnit.query.filter_by(name="Maintenance").first()
        if not User.query.filter_by(email=manager_email).first():
            manager = User(
                name="Unit Manager",
                email=manager_email,
                password=generate_password_hash("Manager@123"),
                role="service_unit_manager",
                service_unit_id=m_unit.id,
                dept="Maintenance",
                is_verified=True
            )
            db.session.add(manager)
            db.session.commit()
            m_unit.manager_id = manager.id
            db.session.commit()
            print("Manager created.")

        # 6. Create Staff
        staff_email = "staff@cdgi.edu.in"
        if not User.query.filter_by(email=staff_email).first():
            staff = User(
                name="Staff Worker",
                email=staff_email,
                password=generate_password_hash("Staff@123"),
                role="staff",
                service_unit_id=m_unit.id,
                dept="Maintenance",
                is_verified=True
            )
            db.session.add(staff)
            print("Staff created.")

        # 7. Create a Student
        student_email = "student@cdgi.edu.in"
        if not User.query.filter_by(email=student_email).first():
            student = User(
                name="John Student",
                email=student_email,
                password=generate_password_hash("Student@123"),
                role="student",
                dept="CSE",
                roll_no="0832CS211001",
                is_verified=True
            )
            db.session.add(student)
            print("Student created.")
        db.session.commit()

        student = User.query.filter_by(email=student_email).first()
        staff = User.query.filter_by(email=staff_email).first()
        m_unit = ServiceUnit.query.filter_by(name="Maintenance").first()

        # 8. Create Mock Complaints
        complaints_data = [
            {
                "ticket_id": "TKT-0001",
                "title": "Water leakage in Lab 102",
                "category": "Plumbing Issue",
                "description": "The water tap is leaking continuously in Lab 102.",
                "status": "resolved",
                "service_unit_id": m_unit.id,
                "assigned_staff_id": staff.id,
                "is_escalated": False,
                "created_at": datetime.utcnow() - timedelta(days=6)
            },
            {
                "ticket_id": "TKT-0002",
                "title": "Broken bench in Auditorium",
                "category": "Plumbing Issue",
                "description": "One of the benches in the front row is broken.",
                "status": "escalated",
                "service_unit_id": m_unit.id,
                "assigned_staff_id": staff.id,
                "is_escalated": True,
                "assigned_at": datetime.utcnow() - timedelta(days=3),
                "escalated_at": datetime.utcnow() - timedelta(days=1),
                "created_at": datetime.utcnow() - timedelta(days=4)
            },
            {
                "ticket_id": "TKT-0003",
                "title": "A/C not cooling in Faculty Room",
                "category": "Fan Not Working",
                "description": "The air conditioner is making noise and not cooling.",
                "status": "in-progress",
                "service_unit_id": m_unit.id,
                "assigned_staff_id": staff.id,
                "is_escalated": False,
                "assigned_at": datetime.utcnow() - timedelta(hours=12),
                "created_at": datetime.utcnow() - timedelta(days=2)
            },
            {
                "ticket_id": "TKT-0004",
                "title": "Lights off in corridor",
                "category": "Fan Not Working",
                "description": "Entire corridor on 2nd floor is dark.",
                "status": "routed",
                "service_unit_id": m_unit.id,
                "is_escalated": False,
                "created_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "ticket_id": "TKT-0005",
                "title": "WiFi signal weak in Library",
                "category": "Internet Down",
                "description": "Very poor connectivity in the reading section.",
                "status": "escalated",
                "service_unit_id": m_unit.id,
                "assigned_staff_id": staff.id,
                "is_escalated": True,
                "assigned_at": datetime.utcnow() - timedelta(days=5),
                "escalated_at": datetime.utcnow() - timedelta(days=3),
                "created_at": datetime.utcnow() - timedelta(days=5)
            },
            {
                "ticket_id": "TKT-0006",
                "title": "Projector not working in CR-1",
                "category": "IT Support",
                "description": "Projector keeps turning off.",
                "status": "resolved",
                "service_unit_id": m_unit.id,
                "is_escalated": False,
                "created_at": datetime.utcnow() - timedelta(days=2)
            },
            {
                "ticket_id": "TKT-0007",
                "title": "Door lock broken",
                "category": "Maintenance",
                "description": "Lab door cannot be locked.",
                "status": "resolved",
                "service_unit_id": m_unit.id,
                "is_escalated": False,
                "created_at": datetime.utcnow() - timedelta(days=3)
            }
        ]

        for c_item in complaints_data:
            if not Complaint.query.filter_by(ticket_id=c_item["ticket_id"]).first():
                c = Complaint(
                    ticket_id=c_item["ticket_id"],
                    title=c_item["title"],
                    category=c_item["category"],
                    description=c_item["description"],
                    status=c_item["status"],
                    user_id=student.id,
                    service_unit_id=c_item.get("service_unit_id"),
                    assigned_staff_id=c_item.get("assigned_staff_id"),
                    is_escalated=c_item["is_escalated"],
                    assigned_at=c_item.get("assigned_at"),
                    escalated_at=c_item.get("escalated_at"),
                    created_at=c_item.get("created_at"),
                    dept=student.dept
                )
                db.session.add(c)
        
        db.session.commit()
        print("Mock complaints added successfully.")

if __name__ == "__main__":
    seed_data()
