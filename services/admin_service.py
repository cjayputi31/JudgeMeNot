import bcrypt
from sqlalchemy.orm import Session, joinedload
from core.database import SessionLocal
from models.all_models import User, Event, AuditLog
import datetime

class AdminService:
    # --- HELPER: LOGGING ---
    def log_action(self, user_id, action, details):
        db: Session = SessionLocal()
        try:
            new_log = AuditLog(
                user_id=user_id,
                action=action,
                details=details,
                timestamp=datetime.datetime.now()
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            print(f"Failed to write log: {e}")
        finally:
            db.close()

    def get_all_users(self):
        db: Session = SessionLocal()
        try:
            return db.query(User).all()
        finally:
            db.close()

    def create_user(self, admin_id, name, username, password, role):
        db: Session = SessionLocal()
        try:
            if db.query(User).filter(User.username == username).first():
                return False, "Username already exists."

            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

            new_user = User(
                name=name,
                username=username,
                password_hash=hashed,
                role=role,
                is_active=True,
                is_pending=False # Admin created users are auto-approved
            )
            db.add(new_user)
            db.commit()

            self.log_action(admin_id, "CREATE_USER", f"Created user '{username}' as {role}")
            return True, "User created successfully."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    # --- UPDATED FUNCTION HERE ---
    def update_user(self, admin_id, user_id, name, username, role, password=None, is_pending=False, is_active=True):
        db: Session = SessionLocal()
        try:
            if not user_id:
                return False, "Invalid User ID"
                
            user = db.query(User).get(user_id)
            if not user: return False, "User not found"

            old_role = user.role
            user.name = name
            user.username = username
            user.role = role
            user.is_pending = is_pending
            user.is_active = is_active

            details = f"Updated profile for '{username}'"
            if old_role != role:
                details += f" (Role: {old_role}->{role})"
            if is_pending is False and is_active is True:
                details += " [Account Approved/Active]"

            if password:
                salt = bcrypt.gensalt()
                user.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
                details += " [Password Changed]"

            db.commit()
            self.log_action(admin_id, "UPDATE_USER", details)
            return True, "User updated successfully."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def delete_user(self, admin_id, user_id):
        db: Session = SessionLocal()
        try:
            user = db.query(User).get(user_id)
            if not user: return False, "User not found"

            username = user.username
            db.delete(user)
            db.commit()

            self.log_action(admin_id, "DELETE_USER", f"Deleted user '{username}'")
            return True, "User deleted successfully."
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

    def create_event(self, admin_id, name, event_type):
        db: Session = SessionLocal()
        try:
            new_event = Event(
                name=name,
                event_type=event_type, 
                status='Active'
            )
            db.add(new_event)
            db.commit()
            self.log_action(admin_id, "CREATE_EVENT", f"Created event '{name}' ({event_type})")
            return True, "Event created successfully."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def get_all_judges(self):
        db = SessionLocal()
        try:
            return db.query(User).filter(User.role == "Judge").all()
        finally:
            db.close()

    def get_security_logs(self):
        db: Session = SessionLocal()
        try:
            return db.query(AuditLog)\
                     .options(joinedload(AuditLog.user))\
                     .order_by(AuditLog.timestamp.desc())\
                     .all()
        finally:
            db.close()