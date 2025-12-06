from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.all_models import Contestant

class ContestantService:
    def add_contestant(self, event_id, number, name, gender, image_path=None):
        db = SessionLocal()
        try:
            # FIX: Check duplicate for specific GENDER only
            exists = db.query(Contestant).filter(
                Contestant.event_id == event_id, 
                Contestant.candidate_number == number,
                Contestant.gender == gender # Allow Male 1 & Female 1
            ).first()
            
            if exists:
                return False, f"Candidate #{number} ({gender}) already exists."

            new_c = Contestant(
                event_id=event_id,
                candidate_number=number,
                name=name,
                gender=gender,
                image_path=image_path
            )
            db.add(new_c)
            db.commit()
            return True, "Contestant added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def get_contestants(self, event_id, active_only=False):
        db = SessionLocal()
        try:
            query = db.query(Contestant).filter(Contestant.event_id == event_id)
            if active_only:
                query = query.filter(Contestant.status == 'Active')
            return query.order_by(Contestant.candidate_number).all()
        finally:
            db.close()

    def delete_contestant(self, contestant_id):
        db = SessionLocal()
        try:
            c = db.query(Contestant).get(contestant_id)
            if c:
                db.delete(c)
                db.commit()
                return True, "Deleted."
            return False, "Not found."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()