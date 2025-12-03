from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import SessionLocal
from models.all_models import Segment, Criteria, Score, Contestant, Event

class PageantService:
    def add_segment(self, event_id, name, weight, order):
        """
        Adds a segment like 'Swimwear' (30%)
        weight: Float between 0.0 and 1.0 (e.g., 0.30)
        """
        db: Session = SessionLocal()
        try:
            new_segment = Segment(
                event_id=event_id,
                name=name,
                percentage_weight=weight,
                order_index=order,
                # Defaults for Pageant
                points_per_question=0,
                total_questions=0
            )
            db.add(new_segment)
            db.commit()
            return True, "Segment added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def add_criteria(self, segment_id, name, weight, max_score=10):
        """
        Adds criteria like 'Poise' (40%) to a segment.
        """
        db: Session = SessionLocal()
        try:
            new_criteria = Criteria(
                segment_id=segment_id,
                name=name,
                weight=weight,
                max_score=max_score
            )
            db.add(new_criteria)
            db.commit()
            return True, "Criteria added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def update_segment(self, segment_id, name, weight):
        """Updates an existing segment"""
        db: Session = SessionLocal()
        try:
            seg = db.query(Segment).get(segment_id)
            if seg:
                seg.name = name
                seg.percentage_weight = weight
                db.commit()
                return True, "Segment updated."
            return False, "Segment not found."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def update_criteria(self, criteria_id, name, weight):
        """Updates an existing criteria"""
        db: Session = SessionLocal()
        try:
            crit = db.query(Criteria).get(criteria_id)
            if crit:
                crit.name = name
                crit.weight = weight
                db.commit()
                return True, "Criteria updated."
            return False, "Criteria not found."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()


    def submit_score(self, judge_id, contestant_id, criteria_id, score_value):
        """
        Saves a single score (e.g., Judge 1 gives 9.5 for Poise).
        Upserts (Updates if exists, Inserts if new) to allow changing scores.
        """
        db: Session = SessionLocal()
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

    def calculate_standing(self, event_id):
        """
        THE COMPLEX MATH:
        1. Average score per criteria across all judges.
        2. Weighted sum of criteria -> Segment Score.
        3. Weighted sum of segments -> Final Score.
        Returns sorted list of dictionaries.
        """
        db: Session = SessionLocal()
        results = []
        try:
            contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()
            segments = db.query(Segment).filter(Segment.event_id == event_id).all()

            for c in contestants:
                total_event_score = 0.0
                
                for s in segments:
                    segment_score = 0.0
                    # Get all criteria for this segment
                    criterias = db.query(Criteria).filter(Criteria.segment_id == s.id).all()
                    
                    for crit in criterias:
                        # Get average score given by judges for this specific criteria
                        avg_score = db.query(func.avg(Score.score_value))\
                            .filter(Score.contestant_id == c.id, Score.criteria_id == crit.id)\
                            .scalar() or 0.0
                        
                        # Apply Criteria Weight (e.g., 9.0 * 0.40 for Poise)
                        segment_score += (avg_score * crit.weight)
                    
                    # Apply Segment Weight (e.g., Swimwear Score * 0.30)
                    total_event_score += (segment_score * s.percentage_weight)
                
                results.append({
                    "contestant_id": c.id,
                    "name": c.name,
                    "candidate_number": c.candidate_number,
                    "total_score": round(total_event_score, 2)
                })

            # Sort by total_score descending
            results.sort(key=lambda x: x['total_score'], reverse=True)
            return results

        finally:
            db.close()