from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import SessionLocal
from models.all_models import Segment, Criteria, Score, Contestant, Event

class PageantService:
    def add_segment(self, event_id, name, weight, order):
        db = SessionLocal()
        try:
            new_segment = Segment(
                event_id=event_id, name=name, percentage_weight=weight, order_index=order,
                points_per_question=0, total_questions=0
            )
            db.add(new_segment)
            db.commit()
            return True, "Segment added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def update_segment(self, segment_id, name, weight):
        db = SessionLocal()
        try:
            seg = db.query(Segment).get(segment_id)
            if seg:
                seg.name = name
                seg.percentage_weight = weight
                db.commit()
                return True, "Updated."
            return False, "Not found."
        finally:
            db.close()

    # --- CHANGED: Default max_score to 100 ---
    def add_criteria(self, segment_id, name, weight, max_score=100):
        db = SessionLocal()
        try:
            new_crit = Criteria(segment_id=segment_id, name=name, weight=weight, max_score=max_score)
            db.add(new_crit)
            db.commit()
            return True, "Criteria added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    # --- CHANGED: Force max_score to 100 on update ---
    def update_criteria(self, criteria_id, name, weight):
        db = SessionLocal()
        try:
            crit = db.query(Criteria).get(criteria_id)
            if crit:
                crit.name = name
                crit.weight = weight
                crit.max_score = 100 # Auto-fix existing criteria to 100
                db.commit()
                return True, "Updated."
            return False, "Not found."
        finally:
            db.close()

    def submit_score(self, judge_id, contestant_id, criteria_id, score_value):
        """
        Saves a single score. Upserts (Updates if exists, Inserts if new).
        """
        db = SessionLocal()
        try:
            # 1. Check if score exists
            existing_score = db.query(Score).filter(
                Score.judge_id == judge_id,
                Score.contestant_id == contestant_id,
                Score.criteria_id == criteria_id
            ).first()

            if existing_score:
                existing_score.score_value = score_value
            else:
                # Need to fetch segment_id from criteria for the Score record
                criteria = db.query(Criteria).get(criteria_id)
                new_score = Score(
                    judge_id=judge_id,
                    contestant_id=contestant_id,
                    criteria_id=criteria_id,
                    segment_id=criteria.segment_id,
                    score_value=score_value
                )
                db.add(new_score)
            
            db.commit()
            return True, "Score saved."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def get_active_pageants(self):
        """Returns all events of type 'Pageant'"""
        db = SessionLocal()
        try:
            return db.query(Event).filter(Event.event_type == "Pageant", Event.status == "Active").all()
        finally:
            db.close()

    def get_event_structure(self, event_id):
        """
        Returns a nested dictionary of Segments -> Criteria
        """
        db = SessionLocal()
        structure = []
        try:
            segments = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
            for seg in segments:
                criterias = db.query(Criteria).filter(Criteria.segment_id == seg.id).all()
                structure.append({
                    "segment": seg,
                    "criteria": criterias
                })
            return structure
        finally:
            db.close()

    def get_judge_scores(self, judge_id, contestant_id):
        """
        Returns a dictionary {criteria_id: score_value}
        """
        db = SessionLocal()
        scores_map = {}
        try:
            scores = db.query(Score).filter(
                Score.judge_id == judge_id, 
                Score.contestant_id == contestant_id
            ).all()
            
            for s in scores:
                if s.criteria_id:
                    scores_map[s.criteria_id] = s.score_value
            return scores_map
        finally:
            db.close()
            
    def calculate_standing(self, event_id):
        """Calculates final scores (Weighted Average)"""
        db = SessionLocal()
        results = []
        try:
            contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()
            segments = db.query(Segment).filter(Segment.event_id == event_id).all()

            for c in contestants:
                total_event_score = 0.0
                
                for s in segments:
                    segment_score = 0.0
                    criterias = db.query(Criteria).filter(Criteria.segment_id == s.id).all()
                    
                    for crit in criterias:
                        avg_score = db.query(func.avg(Score.score_value))\
                            .filter(Score.contestant_id == c.id, Score.criteria_id == crit.id)\
                            .scalar() or 0.0
                        segment_score += (avg_score * crit.weight)
                    
                    total_event_score += (segment_score * s.percentage_weight)
                
                results.append({
                    "contestant_id": c.id,
                    "name": c.name,
                    "candidate_number": c.candidate_number,
                    "total_score": round(total_event_score, 2)
                })

            results.sort(key=lambda x: x['total_score'], reverse=True)
            return results
        finally:
            db.close()