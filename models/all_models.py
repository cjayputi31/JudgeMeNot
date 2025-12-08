import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship, backref
from core.database import Base

# ---------------------------------------------------------
# 1. USERS & ROLES
# ---------------------------------------------------------
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False) # IAS: Hashed
    name = Column(String(100)) 

    # ROLES: 'Admin', 'AdminViewer', 'Judge', 'Tabulator'
    role = Column(String(20), nullable=False) 

    # PERMISSIONS
    is_active = Column(Boolean, default=True)
    is_chairman = Column(Boolean, default=False) # For Pageant Tie-Breakers

    # RELATIONSHIPS
    scores_given = relationship("Score", back_populates="judge")
    audit_logs = relationship("AuditLog", back_populates="user")

# ---------------------------------------------------------
# 2. EVENTS (The "Dual Engine")
# ---------------------------------------------------------
class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False) 
    event_type = Column(String(20), nullable=False) 
    status = Column(String(20), default='Active') 
    is_locked = Column(Boolean, default=False)
    show_public_rankings = Column(Boolean, default=False)

    segments = relationship("Segment", back_populates="event")
    contestants = relationship("Contestant", back_populates="event")

    # NEW RELATIONSHIP
    assigned_judges = relationship("EventJudge", back_populates="event")

class Segment(Base):
    __tablename__ = 'segments'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    name = Column(String(100), nullable=False)
    order_index = Column(Integer)

    # PAGEANT FIELDS
    percentage_weight = Column(Float, default=0.0)
    is_active = Column(Boolean, default=False)

    # NEW: ELIMINATION LOGIC
    is_final = Column(Boolean, default=False) # Is this the "reset" round?
    qualifier_limit = Column(Integer, default=0) # How many get in? (e.g. Top 5)

    # QUIZ BEE FIELDS
    points_per_question = Column(Integer, default=1)
    total_questions = Column(Integer, default=10)

    # NEW: Store IDs of participants allowed in this round (comma-separated: "1,5,9")
    participating_school_ids = Column(String(255), nullable=True) 

    # NEW: Link to Parent Round (for Clinchers to know where they came from)
    related_segment_id = Column(Integer, ForeignKey('segments.id'), nullable=True)
    
    event = relationship("Event", back_populates="segments")
    criteria = relationship("Criteria", back_populates="segment")
    scores = relationship("Score", back_populates="segment")
    
    # Self-referential relationship (optional helper)
    children = relationship("Segment", backref=backref('parent', remote_side=[id]))


class Criteria(Base):
    """Only for Pageants (e.g., 'Poise' 40%)"""
    __tablename__ = 'criteria'

    id = Column(Integer, primary_key=True)
    segment_id = Column(Integer, ForeignKey('segments.id'))
    name = Column(String(100), nullable=False)
    weight = Column(Float, default=1.0) 
    max_score = Column(Integer, default=10)

    segment = relationship("Segment", back_populates="criteria")
    scores = relationship("Score", back_populates="criteria")

# ---------------------------------------------------------
# 3. CONTESTANTS
# ---------------------------------------------------------
class Contestant(Base):
    __tablename__ = 'contestants'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'))

    candidate_number = Column(Integer)
    name = Column(String(100), nullable=False)
    gender = Column(String(10)) 
    status = Column(String(20), default='Active') 

    # NEW: Image Path
    image_path = Column(String(255), nullable=True) 

    assigned_tabulator_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    event = relationship("Event", back_populates="contestants")
    scores = relationship("Score", back_populates="contestant")

# ---------------------------------------------------------
# 4. SCORES & LOGS
# ---------------------------------------------------------
class Score(Base):
    __tablename__ = 'scores'

    id = Column(Integer, primary_key=True)

    # WHO, WHOM, WHERE
    contestant_id = Column(Integer, ForeignKey('contestants.id'))
    judge_id = Column(Integer, ForeignKey('users.id')) 
    segment_id = Column(Integer, ForeignKey('segments.id'))
    criteria_id = Column(Integer, ForeignKey('criteria.id'), nullable=True) 

    # THE SCORE
    score_value = Column(Float, default=0.0) 

    # QUIZ BEE METADATA
    question_number = Column(Integer, nullable=True) 
    is_correct = Column(Boolean, default=False)

    contestant = relationship("Contestant", back_populates="scores")
    judge = relationship("User", back_populates="scores_given")
    segment = relationship("Segment", back_populates="scores")
    criteria = relationship("Criteria", back_populates="scores")

class JudgeProgress(Base):
    __tablename__ = 'judge_progress'

    id = Column(Integer, primary_key=True)
    judge_id = Column(Integer, ForeignKey('users.id'))
    segment_id = Column(Integer, ForeignKey('segments.id'))

    # If True, the judge cannot change scores for this segment anymore
    is_finished = Column(Boolean, default=False) 

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(50)) 
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="audit_logs")

class EventJudge(Base):
    __tablename__ = 'event_judges'

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    judge_id = Column(Integer, ForeignKey('users.id'))

    # Role specific to this event
    is_chairman = Column(Boolean, default=False) 

    event = relationship("Event", back_populates="assigned_judges")