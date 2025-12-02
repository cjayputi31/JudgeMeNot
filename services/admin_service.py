import bcrypt
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.all_models import User, Event

class AdminService:
    def get_all_users(self):
        db: Session = SessionLocal()
        try:
            return db.query(User).all()
        finally:
            db.close()

    def create_user(self, name, username, password, role):
        db: Session = SessionLocal()
        try:
            # Check if username exists
            if db.query(User).filter(User.username == username).first():
                return False, "Username already exists."

            # Hash Password (IAS Requirement)
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

            new_user = User(
                name=name,
                username=username,
                password_hash=hashed,
                role=role,
                is_active=True
            )
            db.add(new_user)
            db.commit()
            return True, "User created successfully."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def get_all_events(self):
        db: Session = SessionLocal()
        try:
            return db.query(Event).all()
        finally:
            db.close()

    def create_event(self, name, event_type):
        db: Session = SessionLocal()
        try:
            new_event = Event(
                name=name,
                event_type=event_type, # 'Pageant' or 'QuizBee'
                status='Active'
            )
            db.add(new_event)
            db.commit()
            return True, "Event created successfully."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()