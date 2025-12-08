from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import SessionLocal
from models.all_models import Segment, Score, Contestant, AuditLog
import datetime

class QuizService:
    def add_round(self, admin_id, event_id, name, points, total_questions, order, is_final=False, qualifier_limit=0, participating_ids=None, related_id=None):
        db: Session = SessionLocal()
        try:
            # Only check order conflict if NOT a clincher (clinchers are appended)
            if not related_id:
                exists = db.query(Segment).filter(Segment.event_id == event_id, Segment.order_index == order).first()
                if exists:
                    return False, f"Round #{order} already exists. Please choose a different sequence number."
                
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
                related_segment_id=related_id, # Link to parent
                percentage_weight=0,
                is_active=False
            )
            db.add(new_round)

            log = AuditLog(user_id=admin_id, action="ADD_ROUND", details=f"Added Round {order}: '{name}'", timestamp=datetime.datetime.now())
            db.add(log)

            db.commit()
            return True, "Round added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def update_round(self, admin_id, round_id, name, points, total_questions, order, is_final, qualifier_limit):
        """
        Updates an existing round.
        """
        db: Session = SessionLocal()
        try:
            target = db.query(Segment).get(round_id)
            if not target:
                return False, "Round not found."

            # Check if new order conflicts with another round (excluding itself)
            if target.order_index != order:
                exists = db.query(Segment).filter(
                    Segment.event_id == target.event_id, 
                    Segment.order_index == order,
                    Segment.id != round_id
                ).first()
                if exists:
                    return False, f"Round #{order} already exists."

            # Update fields
            target.name = name
            target.points_per_question = points
            target.total_questions = total_questions
            target.order_index = order
            target.is_final = is_final
            target.qualifier_limit = qualifier_limit

            # AUDIT LOG
            log = AuditLog(
                user_id=admin_id,
                action="UPDATE_ROUND",
                details=f"Updated Round {order}: '{name}'",
                timestamp=datetime.datetime.now()
            )
            db.add(log)

            db.commit()
            return True, "Round updated."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def delete_round(self, admin_id, round_id):
        """
        Deletes a round and all its associated scores.
        """
        db: Session = SessionLocal()
        try:
            target = db.query(Segment).get(round_id)
            if not target:
                return False, "Round not found."

            round_name = target.name

            # 1. Delete associated scores first (Cascade usually handles this, but explicit is safer)
            db.query(Score).filter(Score.segment_id == round_id).delete()

            # 2. Delete the round
            db.delete(target)

            # AUDIT LOG
            log = AuditLog(
                user_id=admin_id,
                action="DELETE_ROUND",
                details=f"Deleted Round: '{round_name}'",
                timestamp=datetime.datetime.now()
            )
            db.add(log)

            db.commit()
            return True, "Round deleted."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def submit_answer(self, tabulator_id, contestant_id, round_id, question_num, is_correct):
        """
        Records a Correct/Wrong answer.
        """
        db: Session = SessionLocal()
        try:
            # 1. Check if already scored
            existing_score = db.query(Score).filter(
                Score.contestant_id == contestant_id,
                Score.segment_id == round_id,
                Score.question_number == question_num
            ).first()

            # Calculate points immediately based on the round settings
            round_info = db.query(Segment).get(round_id)
            points = round_info.points_per_question if is_correct else 0

            if existing_score:
                existing_score.is_correct = is_correct
                existing_score.score_value = points
                existing_score.judge_id = tabulator_id 
            else:
                new_score = Score(
                    contestant_id=contestant_id,
                    segment_id=round_id,
                    judge_id=tabulator_id,
                    question_number=question_num,
                    is_correct=is_correct,
                    score_value=points
                )
                db.add(new_score)

            db.commit()
            return True, "Answer recorded."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def get_live_scores(self, event_id, specific_round_id=None, limit_to_participants=None):
        """
        Calculates scores.
        - If specific_round_id is set: Returns scores ONLY for that round (resets to 0).
        - If limit_to_participants (list of IDs) is set: Only returns those contestants.
        """
        db: Session = SessionLocal()
        results = []
        try:
            # 1. Determine which contestants to fetch
            query = db.query(Contestant).filter(Contestant.event_id == event_id)

            # --- UPDATED FILTERING LOGIC ---
            # If specific_round_id is set (Clincher OR Normal Round with restrictions), check its participating_ids
            active_segment = None
            if specific_round_id:
                active_segment = db.query(Segment).get(specific_round_id)
            else:
                # If no specific round, try to find the currently active one to apply filtering
                active_segment = db.query(Segment).filter(Segment.event_id == event_id, Segment.is_active == True).first()

            if limit_to_participants:
                query = query.filter(Contestant.id.in_(limit_to_participants))
            elif active_segment and active_segment.participating_school_ids:
                # This logic now applies to ALL rounds that have restrictions (Clinchers AND Average/Difficult)
                p_ids = [int(x) for x in active_segment.participating_school_ids.split(",") if x.strip()]
                query = query.filter(Contestant.id.in_(p_ids))

            contestants = query.all()

            for c in contestants:
                # Summing Logic
                score_query = db.query(func.sum(Score.score_value))\
                    .join(Segment, Score.segment_id == Segment.id)\
                    .filter(Score.contestant_id == c.id, Segment.event_id == event_id)

                # Filter sums by round if specific_round_id is active
                if specific_round_id:
                    score_query = score_query.filter(Score.segment_id == specific_round_id)

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

    def advance_to_next_round(self, admin_id, event_id, current_round_id, qualified_ids):
        """
        1. Deactivates current round.
        2. Finds the next round (chronologically), handling clincher pointers.
        3. Updates next round's participants.
        4. Activates next round.
        """
        db = SessionLocal()
        try:
            current_round = db.query(Segment).get(current_round_id)
            if not current_round: return False, "Current round not found."
            base_order_index = current_round.order_index
            if current_round.related_segment_id:
                parent = db.query(Segment).get(current_round.related_segment_id)
                if parent:
                    base_order_index = parent.order_index
            
            # --- FIND NEXT NORMAL ROUND ---
            # We look for the lowest order index that is strictly greater than the base order
            # AND is not a clincher (optional check, but order logic should suffice)
            next_round = db.query(Segment).filter(
                Segment.event_id == event_id,
                Segment.order_index > base_order_index
            ).order_by(Segment.order_index).first()

            if not next_round:
                return False, "No next round defined! Add a round first."

            # 2. Deactivate Current
            current_round.is_active = False

            # 3. Setup Next Round
            existing_ids = []
            if next_round.participating_school_ids:
                existing_ids = [int(x) for x in next_round.participating_school_ids.split(",") if x.strip()]

            combined_ids = list(set(existing_ids + qualified_ids))
            next_round.participating_school_ids = ",".join(map(str, combined_ids))
            next_round.is_active = True

            # Log
            log = AuditLog(
                user_id=admin_id,
                action="ADVANCE_ROUND",
                details=f"Advanced to '{next_round.name}' (Base Order: {base_order_index} -> {next_round.order_index})",
                timestamp=datetime.datetime.now()
            )
            db.add(log)

            db.commit()
            return True, f"Advanced to {next_round.name}"
        except Exception as e:
            return False, str(e)
        finally:
            db.close()


    def initialize_contestant_round(self, contestant_id, round_id):
        pass