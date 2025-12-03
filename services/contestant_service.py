from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.all_models import Contestant

# NOTE: Do NOT import ContestantService here. It is defined below.

class ContestantService:
    def add_contestant(self, event_id, number, name, gender=None):
        """
        Adds a candidate.
        number: Integer (e.g., 1 for Candidate #1)
        gender: Optional (for Pageants)
        """
        db: Session = SessionLocal()
        try:
            # Check for duplicate number in this event
            exists = db.query(Contestant).filter(
                Contestant.event_id == event_id, 
                Contestant.candidate_number == number
            ).first()
            
            if exists:
                return False, f"Candidate #{number} already exists."

            new_c = Contestant(
                event_id=event_id,
                candidate_number=number,
                name=name,
                gender=gender
            )
            db.add(new_c)
            db.commit()
            return True, "Contestant added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def get_contestants(self, event_id):
        db: Session = SessionLocal()
        try:
            # Return sorted by candidate number
            return db.query(Contestant).filter(Contestant.event_id == event_id)\
                     .order_by(Contestant.candidate_number).all()
        finally:
            db.close()

    def delete_contestant(self, contestant_id):
        db: Session = SessionLocal()
        try:
            c = db.query(Contestant).get(contestant_id)
            if c:
                db.delete(c)
                db.commit()
                return True, "Contestant deleted."
            return False, "Not found."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()