from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.all_models import Contestant

class ContestantService:
    def add_contestant(self, event_id, number, name, gender, image_path=None):
        db = SessionLocal()
        try:
            # Check duplicate number for specific gender
            exists = db.query(Contestant).filter(
                Contestant.event_id == event_id, 
                Contestant.candidate_number == number,
                Contestant.gender == gender
            ).first()

            if exists:
                return False, f"Candidate #{number} ({gender}) already exists."

            new_c = Contestant(
                event_id=event_id,
                candidate_number=number,
                name=name,
                gender=gender,
                image_path=image_path,
                status="Active"
            )
            db.add(new_c)
            db.commit()
            return True, "Contestant added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def update_contestant(self, contestant_id, number, name, gender, image_path=None):
        db = SessionLocal()
        try:
            c = db.query(Contestant).get(contestant_id)
            if not c:
                return False, "Contestant not found."

            # Check duplicate only if number or gender changed
            if c.candidate_number != number or c.gender != gender:
                exists = db.query(Contestant).filter(
                    Contestant.event_id == c.event_id, 
                    Contestant.candidate_number == number,
                    Contestant.gender == gender
                ).first()
                if exists: 
                    return False, f"Candidate #{number} ({gender}) already exists."

            c.candidate_number = number
            c.name = name
            c.gender = gender
            
            # Only update image if a new one was provided
            if image_path:
                c.image_path = image_path
            
            db.commit()
            return True, "Contestant updated."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def delete_contestant(self, contestant_id):
        db = SessionLocal()
        try:
            target = db.query(Contestant).get(contestant_id)
            if not target: 
                return False, "Not found."
            
            event_id = target.event_id
            deleted_number = target.candidate_number
            
            # 1. Delete the contestant
            db.delete(target)
            
            # 2. AUTO-REORDER: Shift numbers down for everyone above this number
            # (e.g. if #2 is deleted, #3 becomes #2)
            higher_candidates = db.query(Contestant).filter(
                Contestant.event_id == event_id,
                Contestant.candidate_number > deleted_number
            ).all()
            
            for c in higher_candidates:
                c.candidate_number -= 1
            
            db.commit()
            return True, "Deleted and reordered."
        except Exception as e:
            db.rollback()
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