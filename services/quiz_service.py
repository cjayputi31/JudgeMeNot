from sqlalchemy.orm import Session
from sqlalchemy import func
from core.database import SessionLocal
from models.all_models import Segment, Score, Contestant

class QuizService:
    def add_round(self, event_id, name, points, total_questions, order):
        """
        Adds a round like 'Easy Round' (1pt per question)
        """
        db: Session = SessionLocal()
        try:
            new_round = Segment(
                event_id=event_id,
                name=name,
                points_per_question=points,  # Stored here
                total_questions=total_questions,
                order_index=order,
                # Defaults for Quiz
                percentage_weight=0 
            )
            db.add(new_round)
            db.commit()
            return True, "Round added."
        except Exception as e:
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
                existing_score.judge_id = tabulator_id # Tabulator acts as judge here
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

    def get_live_scores(self, event_id):
        """
        Simple Summation for Live View.
        Returns list sorted by Total Points.
        """
        db: Session = SessionLocal()
        results = []
        try:
            contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()
            
            for c in contestants:
                # Sum of all 'score_value' for this contestant in this event
                # Note: We join Segment to ensure we only sum scores for THIS event
                total_points = db.query(func.sum(Score.score_value))\
                    .join(Segment, Score.segment_id == Segment.id)\
                    .filter(Score.contestant_id == c.id, Segment.event_id == event_id)\
                    .scalar() or 0.0
                
                results.append({
                    "contestant_id": c.id,
                    "name": c.name,
                    "total_score": int(total_points) # Quiz scores are usually integers
                })

            results.sort(key=lambda x: x['total_score'], reverse=True)
            return results

        finally:
            db.close()