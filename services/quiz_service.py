from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import SessionLocal
from models.all_models import Segment, Score, Contestant, AuditLog
import datetime

class QuizService:
    def add_round(self, admin_id, event_id, name, points, total_questions, order, is_final=False, qualifier_limit=0, participating_ids=None):
        db: Session = SessionLocal()
        try:
            # Check order conflict only if not a clincher (clinchers share order or strictly follow)
            # Actually, let's just check standard conflict
            exists = db.query(Segment).filter(Segment.event_id == event_id, Segment.order_index == order).first()
            # If inserting a clincher, we might have overlapping orders, or we should have shifted orders.
            # For simplicity, we allow add_round to proceed if we manage orders externally, 
            # but here we'll just warn.
            if exists and "Clincher" not in name:
                 return False, f"Round #{order} already exists."

            p_ids_str = None
            if participating_ids:
                p_ids_str = ",".join(map(str, participating_ids))

            new_round = Segment(
                event_id=event_id,
                name=name,
                points_per_question=points,
                total_questions=total_questions,
                order_index=order,
                is_final=is_final,
                qualifier_limit=qualifier_limit,
                participating_school_ids=p_ids_str,
                percentage_weight=0,
                is_active=False
            )
            db.add(new_round)
            
            log = AuditLog(
                user_id=admin_id,
                action="ADD_ROUND",
                details=f"Added Round {order}: '{name}'",
                timestamp=datetime.datetime.now()
            )
            db.add(log)
            
            db.commit()
            return True, "Round added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()
    
    def update_round(self, admin_id, round_id, name, points, total_questions, order, is_final, qualifier_limit):
        db: Session = SessionLocal()
        try:
            target = db.query(Segment).get(round_id)
            if not target: return False, "Round not found."

            if target.order_index != order:
                exists = db.query(Segment).filter(Segment.event_id == target.event_id, Segment.order_index == order, Segment.id != round_id).first()
                if exists: return False, f"Round #{order} already exists."

            target.name = name; target.points_per_question = points; target.total_questions = total_questions
            target.order_index = order; target.is_final = is_final; target.qualifier_limit = qualifier_limit
            
            log = AuditLog(user_id=admin_id, action="UPDATE_ROUND", details=f"Updated Round {order}: '{name}'", timestamp=datetime.datetime.now())
            db.add(log)
            db.commit()
            return True, "Round updated."
        except Exception as e: return False, str(e)
        finally: db.close()

    def submit_answer(self, tabulator_id, contestant_id, round_id, question_num, is_correct):
        db: Session = SessionLocal()
        try:
            existing = db.query(Score).filter(Score.contestant_id == contestant_id, Score.segment_id == round_id, Score.question_number == question_num).first()
            round_info = db.query(Segment).get(round_id)
            points = round_info.points_per_question if is_correct else 0

            if existing:
                existing.is_correct = is_correct; existing.score_value = points; existing.judge_id = tabulator_id
            else:
                db.add(Score(contestant_id=contestant_id, segment_id=round_id, judge_id=tabulator_id, question_number=question_num, is_correct=is_correct, score_value=points))

            db.commit()

            return True, "Saved."
        except Exception as e: return False, str(e)
        finally: db.close()
    
    def get_live_scores(self, event_id, specific_round_id=None, limit_to_participants=None):
        """Calculates scores based on Round Type.
        1. Clincher (specific_round_id set): Only scores for that round.
        2. Final Round (is_final=True): Only scores for that round (Reset).
        3. Normal Round: Cumulative scores of all PREVIOUS Non-Final + Non-Clincher rounds.
        """
        db: Session = SessionLocal()
        results = []
        try:
            # 1. Determine active context
            active_segment = None
            if specific_round_id:
                active_segment = db.query(Segment).get(specific_round_id)
            else:
                # If no specific round, assume we want the "Cumulative" view for the *currently active* round
                # or just the latest state. 
                active_segment = db.query(Segment).filter(Segment.event_id == event_id, Segment.is_active == True).first()

            # 2. Filter Contestants
            # Start with all, then filter 'Eliminated'
            query = db.query(Contestant).filter(Contestant.event_id == event_id, Contestant.status != 'Eliminated')
            
            if limit_to_participants:
                query = query.filter(Contestant.id.in_(limit_to_participants))
            elif active_segment and active_segment.participating_school_ids:
                # If active round has restricted list (Clincher), only show them
                p_ids = [int(x) for x in active_segment.participating_school_ids.split(",") if x.strip()]
                query = query.filter(Contestant.id.in_(p_ids))

            contestants = query.all()
            
            # 3. Calculate Scores
            for c in contestants:
                score_query = db.query(func.sum(Score.score_value)).join(Segment, Score.segment_id == Segment.id).filter(Score.contestant_id == c.id, Segment.event_id == event_id)
                
                # RULE IMPLEMENTATION:
                if active_segment:
                    if "Clincher" in active_segment.name:
                        # Rule: Clincher scores are isolated (start at 0)
                        score_query = score_query.filter(Score.segment_id == active_segment.id)
                    
                    elif active_segment.is_final:
                        # Rule: Final round resets scores (start at 0)
                        score_query = score_query.filter(Segment.is_final == True)
                    
                    else:
                        # Rule: Normal Round = Cumulative of all Non-Final, Non-Clincher rounds
                        # We exclude clinchers from the main tally
                        score_query = score_query.filter(
                            Segment.is_final == False,
                            Segment.name.notlike("%Clincher%")
                        )
                else:
                    # Default View (No active round?): Show total cumulative
                    score_query = score_query.filter(Segment.is_final == False, Segment.name.notlike("%Clincher%"))

                total_points = score_query.scalar() or 0.0

                results.append({
                    "contestant_id": c.id,
                    "name": c.name,
                    "total_score": int(total_points) 
                })

            results.sort(key=lambda x: x['total_score'], reverse=True)
            return results
        
        finally:
            db.close()

    def eliminate_contestants(self, event_id, keeping_ids):
        """
        Sets status='Eliminated' for everyone NOT in keeping_ids
        """
        db = SessionLocal()
        try:
            contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()
            count = 0
            for c in contestants:
                if c.id not in keeping_ids:
                    c.status = 'Eliminated'
                    count += 1
                else:
                    c.status = 'Active' # Ensure survivors are active
            db.commit()
            return True, f"Eliminated {count} participants."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()