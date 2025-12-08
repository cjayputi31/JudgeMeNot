from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import SessionLocal
from models.all_models import Segment, Score, Contestant, AuditLog
import datetime

class QuizService:
    # ... (Keep add_round, update_round, submit_answer as is) ...
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
        - Filters out 'Eliminated' contestants automatically.
        - Auto-detects if the active round requires "Back to Zero" (Final/Clincher).
        """
        db: Session = SessionLocal()
        results = []
        try:
            # 1. Determine the context
            target_round_id = specific_round_id

            active_segment = None
            if not target_round_id:
                active_segment = db.query(Segment).filter(Segment.event_id == event_id, Segment.is_active == True).first()
                if active_segment:
                    if active_segment.is_final or "Clincher" in active_segment.name:
                        target_round_id = active_segment.id
            
            if target_round_id and not active_segment:
                active_segment = db.query(Segment).get(target_round_id)

            # 2. Determine Contestants to Fetch
            query = db.query(Contestant).filter(Contestant.event_id == event_id)
            
            # --- UPDATE: FILTER ELIMINATED CONTESTANTS ---
            query = query.filter(Contestant.status == 'Active')
            
            # Apply Participant Filters
            if limit_to_participants:
                query = query.filter(Contestant.id.in_(limit_to_participants))
            elif target_round_id and active_segment and active_segment.participating_school_ids:
                p_ids = [int(x) for x in active_segment.participating_school_ids.split(",") if x.strip()]
                query = query.filter(Contestant.id.in_(p_ids))

            contestants = query.all()

            # 3. Calculate Scores
            for c in contestants:
                score_query = db.query(func.sum(Score.score_value))\
                    .join(Segment, Score.segment_id == Segment.id)\
                    .filter(Score.contestant_id == c.id, Segment.event_id == event_id)

                if target_round_id:
                    score_query = score_query.filter(Score.segment_id == target_round_id)

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

    def check_round_ties(self, event_id, round_id, limit):
        scores = self.get_live_scores(event_id, specific_round_id=round_id)
        if len(scores) <= limit:
            return False, scores, [], 0

        last_in_score = scores[limit-1]['total_score']
        first_out_score = scores[limit]['total_score']

        if last_in_score == first_out_score:
            clean_winners = [s for s in scores if s['total_score'] > last_in_score]
            tied_contestants = [s for s in scores if s['total_score'] == last_in_score]
            spots_remaining = limit - len(clean_winners)
            return True, clean_winners, tied_contestants, spots_remaining
        
        return False, scores[:limit], [], 0

    def advance_to_next_round(self, admin_id, event_id, current_round_id, qualified_ids):
        """
        Advances qualified_ids to next round AND eliminates those who failed to qualify.
        """
        db = SessionLocal()
        try:
            current_round = db.query(Segment).get(current_round_id)
            if not current_round: return False, "Current round not found."
            
            # --- UPDATE: ELIMINATION LOGIC ---
            # 1. Identify who was at risk in the CURRENT round
            if current_round.participating_school_ids:
                # E.g. Clincher: Only participants of this clincher are at risk
                p_ids = [int(x) for x in current_round.participating_school_ids.split(",") if x.strip()]
                participants_at_risk = db.query(Contestant).filter(Contestant.id.in_(p_ids)).all()
            else:
                # E.g. Normal Round: Everyone currently active is at risk
                participants_at_risk = db.query(Contestant).filter(
                    Contestant.event_id == event_id,
                    Contestant.status == 'Active'
                ).all()

            # 2. Mark losers as Eliminated
            for c in participants_at_risk:
                if c.id not in qualified_ids:
                    c.status = 'Eliminated'

            # --- NEXT ROUND FINDING LOGIC ---
            base_order_index = current_round.order_index
            if current_round.related_segment_id:
                parent = db.query(Segment).get(current_round.related_segment_id)
                if parent:
                    base_order_index = parent.order_index

            next_round = db.query(Segment).filter(
                Segment.event_id == event_id,              
                Segment.order_index > base_order_index,
                Segment.related_segment_id == None 
            ).order_by(Segment.order_index).first()

            if not next_round:
                # Even if no next round, the elimination above is valid (Event Over).
                db.commit()
                return True, "Event Concluded. Losers eliminated."

            # 3. Deactivate Current
            current_round.is_active = False

            # 4. Setup Next Round (Clean Winners + New Qualifiers)
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
                details=f"Advanced to '{next_round.name}'. Elimination processed.",
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