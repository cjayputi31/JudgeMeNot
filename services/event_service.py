from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from core.database import SessionLocal
from models.all_models import Event, Segment, EventJudge, User, Contestant, AuditLog
import datetime

class EventService:
    # ---------------------------------------------------------
    # EVENT FETCHING
    # ---------------------------------------------------------
    def get_active_events(self, event_type=None):
        db = SessionLocal()
        try:
            query = db.query(Event).filter(Event.status == "Active")
            if event_type:
                query = query.filter(Event.event_type == event_type)
            return query.all()
        finally:
            db.close()

    def get_judge_events(self, judge_id):
        """Returns ONLY events assigned to a specific judge that are Active"""
        db = SessionLocal()
        try:
            return db.query(Event).join(EventJudge).filter(
                EventJudge.judge_id == judge_id,
                Event.status == 'Active'
            ).all()
        finally:
            db.close()

    def is_judge_assigned(self, judge_id, event_id):
        """Security check: verify assignment before entering"""
        db = SessionLocal()
        try:
            exists = db.query(EventJudge).filter(
                EventJudge.judge_id == judge_id,
                EventJudge.event_id == event_id
            ).first()
            return exists is not None
        finally:
            db.close()

    # ---------------------------------------------------------
    # SEGMENT MANAGEMENT
    # ---------------------------------------------------------
    def add_segment(self, event_id, name, weight, order, is_final=False, limit=0):
        db = SessionLocal()
        try:
            if not is_final:
                current_total = db.query(func.sum(Segment.percentage_weight))\
                    .filter(Segment.event_id == event_id, Segment.is_final == False).scalar() or 0.0

                if (current_total + weight) > 1.0001:
                    return False, f"Prelim total exceeds 100%. Current: {int(current_total*100)}%, Adding: {int(weight*100)}%"

            new_segment = Segment(
                event_id=event_id, name=name, percentage_weight=weight, order_index=order,
                is_final=is_final, qualifier_limit=limit,
                points_per_question=0, total_questions=0,
                is_active=False
            )
            db.add(new_segment)
            db.commit()
            return True, "Segment added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def update_segment(self, segment_id, name, weight, is_final, limit):
        db = SessionLocal()
        try:
            seg = db.query(Segment).get(segment_id)
            if seg:
                if not is_final:
                    current_total = db.query(func.sum(Segment.percentage_weight))\
                        .filter(Segment.event_id == seg.event_id, Segment.id != segment_id, Segment.is_final == False).scalar() or 0.0

                    if (current_total + weight) > 1.0001:
                        return False, f"Prelim total exceeds 100%. Current: {int(current_total*100)}%"

                seg.name = name
                seg.percentage_weight = weight
                seg.is_final = is_final
                seg.qualifier_limit = limit
                db.commit()
                return True, "Updated."
            return False, "Not found."
        finally:
            db.close()

    # ---------------------------------------------------------
    # ACTIVE SEGMENT CONTROL
    # ---------------------------------------------------------
    def set_active_segment(self, event_id, segment_id):
        db = SessionLocal()
        try:
            segments = db.query(Segment).filter(Segment.event_id == event_id).all()
            for seg in segments:
                seg.is_active = False

            if segment_id:
                target = db.query(Segment).get(segment_id)
                if target:
                    target.is_active = True
                    msg = f"Segment '{target.name}' is now ACTIVE."

                    if not target.is_final:
                        contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()
                        for c in contestants:
                            c.status = 'Active'
                        msg += " (Contestants Reset)"
                else:
                    msg = "Segment not found."
            else:
                msg = "All segments deactivated."

            db.commit()
            return True, msg
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def get_active_segment(self, event_id):
        db = SessionLocal()
        try:
            return db.query(Segment).filter(
                Segment.event_id == event_id, 
                Segment.is_active == True
            ).first()
        finally:
            db.close()

    # ---------------------------------------------------------
    # JUDGE ASSIGNMENT
    # ---------------------------------------------------------
    def assign_judge(self, event_id, judge_id, is_chairman=False):
        db = SessionLocal()
        try:
            exists = db.query(EventJudge).filter(EventJudge.event_id == event_id, EventJudge.judge_id == judge_id).first()

            if exists:
                exists.is_chairman = is_chairman
                db.commit()
                return True, "Judge role updated."

            new_assign = EventJudge(event_id=event_id, judge_id=judge_id, is_chairman=is_chairman)
            db.add(new_assign)
            db.commit()
            return True, "Judge assigned."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def remove_judge(self, assignment_id):
        db = SessionLocal()
        try:
            assign = db.query(EventJudge).get(assignment_id)
            if assign:
                db.delete(assign)
                db.commit()
                return True, "Judge removed."
            return False, "Not found."
        finally:
            db.close()

    def get_assigned_judges(self, event_id):
        db = SessionLocal()
        try:
            return db.query(EventJudge).options(joinedload(EventJudge.judge))\
                     .filter(EventJudge.event_id == event_id).all()
        finally:
            db.close()
        
    def update_event_status(self, admin_id, event_id, status):
        """Updates the status of an event (e.g. 'Active', 'Ended')"""
        db = SessionLocal()
        try:
            event = db.query(Event).get(event_id)
            if event:
                event.status = status
                
                # AUDIT LOG
                log = AuditLog(
                    user_id=admin_id, 
                    action="UPDATE_EVENT_STATUS", 
                    details=f"Changed event '{event.name}' status to {status}", 
                    timestamp=datetime.datetime.now()
                )
                db.add(log)
                
                db.commit()
                return True, f"Event set to {status}"
            return False, "Event not found"
        except Exception as e:
            return False, str(e)
        finally:
            db.close()