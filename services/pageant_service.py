from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from core.database import SessionLocal
from models.all_models import Segment, Criteria, Score, Contestant, Event, User, JudgeProgress, EventJudge

class PageantService:
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
    # CRITERIA MANAGEMENT
    # ---------------------------------------------------------
    def add_criteria(self, segment_id, name, weight, max_score=100):
        db = SessionLocal()
        try:
            current_total = db.query(func.sum(Criteria.weight))\
                .filter(Criteria.segment_id == segment_id).scalar() or 0.0

            if (current_total + weight) > 1.0001:
                return False, f"Criteria total exceeds 100%. Current: {int(current_total*100)}%"

            new_crit = Criteria(segment_id=segment_id, name=name, weight=weight, max_score=max_score)
            db.add(new_crit)
            db.commit()
            return True, "Criteria added."
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    def update_criteria(self, criteria_id, name, weight):
        db = SessionLocal()
        try:
            crit = db.query(Criteria).get(criteria_id)
            if crit:
                current_total = db.query(func.sum(Criteria.weight))\
                    .filter(Criteria.segment_id == crit.segment_id, Criteria.id != criteria_id).scalar() or 0.0
                if (current_total + weight) > 1.0001:
                    return False, f"Criteria total exceeds 100%. Current: {int(current_total*100)}%"

                crit.name = name
                crit.weight = weight
                crit.max_score = 100 
                db.commit()
                return True, "Updated."
            return False, "Not found."
        finally:
            db.close()

    # ---------------------------------------------------------
    # SCORING & UTILS
    # ---------------------------------------------------------
    def submit_score(self, judge_id, contestant_id, criteria_id, score_value):
        db = SessionLocal()
        try:
            existing_score = db.query(Score).filter(
                Score.judge_id == judge_id,
                Score.contestant_id == contestant_id,
                Score.criteria_id == criteria_id
            ).first()

            if existing_score:
                existing_score.score_value = score_value
            else:
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
        db = SessionLocal()
        try:
            return db.query(Event).filter(Event.event_type == "Pageant", Event.status == "Active").all()
        finally:
            db.close()

    def get_event_structure(self, event_id):
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

    def get_overall_breakdown(self, event_id):
        db = SessionLocal()
        try:
            # 1. Get Segments
            segments = db.query(Segment).filter(Segment.event_id == event_id, Segment.is_final == False).order_by(Segment.order_index).all()
            segment_names = [s.name for s in segments]

            # 2. Get Contestants
            contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()

            # 3. Get Judges (Added this part)
            assigned = db.query(User).join(EventJudge).filter(EventJudge.event_id == event_id).order_by(User.name).all()
            judge_list = [u.name for u in assigned]
            
            data = {'Male': [], 'Female': []}

            for c in contestants:
                row = {
                    "number": c.candidate_number,
                    "name": c.name,
                    "segment_scores": [],
                    "total": 0.0
                }

                overall_weighted_score = 0.0

                for s in segments:
                    segment_raw_score = 0.0
                    criterias = db.query(Criteria).filter(Criteria.segment_id == s.id).all()
                    for crit in criterias:
                        avg = db.query(func.avg(Score.score_value))\
                            .filter(Score.contestant_id == c.id, Score.criteria_id == crit.id)\
                            .scalar() or 0.0
                        segment_raw_score += (avg * crit.weight)

                    row['segment_scores'].append(round(segment_raw_score, 2))
                    overall_weighted_score += (segment_raw_score * s.percentage_weight)

                row['total'] = round(overall_weighted_score, 2)

                if c.gender in data:
                    data[c.gender].append(row)
            for gender in ['Male', 'Female']:
                data[gender].sort(key=lambda x: x['total'], reverse=True)
                for i, r in enumerate(data[gender]):
                    r['rank'] = i + 1

            # Return includes 'judges' now
            return {
                'segments': segment_names,
                'judges': judge_list, 
                'Male': data['Male'],
                'Female': data['Female']
            }
        
        finally:
            db.close()

        # ---------------------------------------------------------
        # TABULATION MATRIX
        # ---------------------------------------------------------
    def get_segment_tabulation(self, event_id, segment_id):
        db = SessionLocal()
        try:
            assigned = db.query(User).join(EventJudge).filter(EventJudge.event_id == event_id).order_by(User.name).all()
            judge_list = [u.name for u in assigned]
            judge_ids = [u.id for u in assigned]

            contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()
            criterias = db.query(Criteria).filter(Criteria.segment_id == segment_id).all()

            data = {'Male': [], 'Female': []}

            for c in contestants:
                row = {
                    "number": c.candidate_number,
                    "name": c.name,
                    "scores": [],
                    "total": 0.0
                }

                judge_totals = []
                for j_id in judge_ids:
                    j_score = 0.0
                    for crit in criterias:
                        val = db.query(Score.score_value).filter(
                            Score.contestant_id == c.id, 
                            Score.judge_id == j_id, 
                            Score.criteria_id == crit.id
                        ).scalar() or 0.0
                        j_score += (val * crit.weight)

                    judge_totals.append(round(j_score, 2))
                row['scores'] = judge_totals

                if judge_totals:
                    row['total'] = round(sum(judge_totals) / len(judge_totals), 2)

                if c.gender in data:
                    data[c.gender].append(row)
            for gender in ['Male', 'Female']:
                data[gender].sort(key=lambda x: x['total'], reverse=True)
                for i, r in enumerate(data[gender]):
                    r['rank'] = i + 1

            return {
                'judges': judge_list,
                'Male': data['Male'],
                'Female': data['Female']
            }
        
        finally:
            db.close()

    def get_all_scores_detailed(self, event_id):

        db = SessionLocal()
        try:
            results = db.query(
                Score, Contestant.name.label("c_name"), User.name.label("j_name"),
                Criteria.name.label("crit_name"), Segment.name.label("seg_name")
            ).join(Contestant, Score.contestant_id == Contestant.id)\
             .join(User, Score.judge_id == User.id)\
             .join(Criteria, Score.criteria_id == Criteria.id)\
             .join(Segment, Score.segment_id == Segment.id)\
             .filter(Segment.event_id == event_id)\
             .order_by(Segment.order_index, Contestant.candidate_number, User.name).all()

            data = []
            for row in results:
                score_obj, c_name, j_name, crit_name, seg_name = row
                data.append({
                    "segment": seg_name, "candidate": c_name, "judge": j_name,
                    "criteria": crit_name, "score": score_obj.score_value
                })
            return data
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
    # JUDGE PROGRESS
    # ---------------------------------------------------------
    def mark_judge_finished(self, judge_id, segment_id):
        db = SessionLocal()
        try:
            prog = db.query(JudgeProgress).filter(JudgeProgress.judge_id == judge_id, JudgeProgress.segment_id == segment_id).first()
            if prog: prog.is_finished = True
            else: db.add(JudgeProgress(judge_id=judge_id, segment_id=segment_id, is_finished=True))
            db.commit()
            return True
        except: return False
        finally: db.close()

    def has_judge_finished(self, judge_id, segment_id):
        db = SessionLocal()
        try:
            prog = db.query(JudgeProgress).filter(JudgeProgress.judge_id == judge_id, JudgeProgress.segment_id == segment_id, JudgeProgress.is_finished == True).first()
            return prog is not None
        finally:
            db.close()

    # ---------------------------------------------------------
    # ELIMINATION ENGINE
    # ---------------------------------------------------------
    def get_preliminary_rankings(self, event_id):
        db = SessionLocal()
        results = {'Male': [], 'Female': []}
        try:
            contestants = db.query(Contestant).filter(Contestant.event_id == event_id).all()
            segments = db.query(Segment).filter(Segment.event_id == event_id, Segment.is_final == False).all()

            for c in contestants:
                total_score = 0.0
                for s in segments:
                    segment_score = 0.0
                    criterias = db.query(Criteria).filter(Criteria.segment_id == s.id).all()
                    for crit in criterias:
                        avg = db.query(func.avg(Score.score_value))\
                            .filter(Score.contestant_id == c.id, Score.criteria_id == crit.id)\
                            .scalar() or 0.0
                        segment_score += (avg * crit.weight)
                    total_score += (segment_score * s.percentage_weight)

                entry = {"contestant": c, "score": round(total_score, 2)}
                if c.gender in results:
                    results[c.gender].append(entry)

            results['Male'].sort(key=lambda x: x['score'], reverse=True)
            results['Female'].sort(key=lambda x: x['score'], reverse=True)
            return results
        finally:
            db.close()

    def activate_final_round(self, event_id, segment_id, limit):
        db = SessionLocal()
        try:
            rankings = self.get_preliminary_rankings(event_id)
            qualifiers = []
            eliminated = []

            for i, entry in enumerate(rankings['Male']):
                c = db.query(Contestant).get(entry['contestant'].id)
                if i < limit:
                    c.status = 'Active'
                    qualifiers.append(f"{c.name} (Male)")
                else:
                    c.status = 'Eliminated'
                    eliminated.append(f"{c.name} (Male)")

            for i, entry in enumerate(rankings['Female']):
                c = db.query(Contestant).get(entry['contestant'].id)
                if i < limit:
                    c.status = 'Active'
                    qualifiers.append(f"{c.name} (Female)")
                else:
                    c.status = 'Eliminated'
                    eliminated.append(f"{c.name} (Female)")

            segments = db.query(Segment).filter(Segment.event_id == event_id).all()
            for s in segments:
                s.is_active = (s.id == segment_id)

            db.commit()
            return True, qualifiers, eliminated
        except Exception as e:
            return False, [], []
        finally:
            db.close()