import bcrypt
from sqlalchemy.orm import Session
from models.all_models import User
from core.database import SessionLocal

class AuthService:
    def login(self, username, password):
        """
        Verifies credentials. 
        Returns: The User object if successful, None if failed.
        """
        db: Session = SessionLocal()
        try:
            # 1. Find the user
            user = db.query(User).filter(User.username == username).first()

            if not user:
                return None

            # 2. Check Password (using bcrypt)
            if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                if not user.is_active:
                    return "DISABLED" 
                if user.is_pending:
                    return "PENDING"
                return user
            else:
                return None
        except Exception as e:
            print(f"Login Error: {e}")
            return None
        finally:
            db.close()

    def get_user_by_id(self, user_id):
        """Helper to retrieve user details during session check"""
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()

    def get_user_by_google_id(self, google_id):
        """Retrieves a user based on their Google ID."""
        db = SessionLocal()
        try:
            return db.query(User).filter(User.google_id == google_id).first()
        finally:
            db.close()

    def register_self_service(self, name, username, password, role, email=None, google_id=None):
        """Registers a new user (Judge/Tabulator) and sets them to pending if manual."""
        db = SessionLocal()
        try:
            # 1. Check for existing username/email
            if username:
                if db.query(User).filter(User.username == username).first():
                    return False, "Username already exists."
            
            # 2. Prepare Data
            is_pending = True # Default to pending for safety
            
            # Note: You can relax is_pending for Google Users if you trust Google Auth
            if google_id:
                is_pending = False 

            hashed_password = None
            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            new_user = User(
                name=name,
                username=username,
                password_hash=hashed_password,
                role=role, 
                email=email,
                google_id=google_id,
                is_pending=is_pending,
                is_active=True
            )
            
            db.add(new_user)
            db.commit()
            return True, "Account created."
            
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()