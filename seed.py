import os
from sqlalchemy.orm import Session
from core.database import SessionLocal, engine, Base
from models.all_models import User, Event, Segment, Criteria, Contestant
import bcrypt

def seed_database():
    print("🌱 Seeding Database...")
    
    # 1. Reset Tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()

    try:
        # 2. Create Users
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), salt).decode('utf-8')
        admin = User(username="admin", password_hash=hashed, name="Super Admin", role="Admin", is_active=True)
        db.add(admin)

        hashed_j = bcrypt.hashpw("judge1".encode('utf-8'), salt).decode('utf-8')
        judge = User(username="judge1", password_hash=hashed_j, name="Judge One", role="Judge", is_active=True)
        db.add(judge)

        # 3. Create Pageant Event
        event = Event(name="Mr. & Ms. Intramurals 2025", event_type="Pageant", status="Active")
        db.add(event)
        db.commit()

        print(f"✅ Created Event: {event.name}")

        # 4. Create Segments
        # Segment 1: Production (Active)
        seg1 = Segment(event_id=event.id, name="Production Number", order_index=1, percentage_weight=0.30, is_active=True, is_final=False)
        db.add(seg1)
        
        # Segment 2: Swimwear
        seg2 = Segment(event_id=event.id, name="Swimwear Competition", order_index=2, percentage_weight=0.30, is_active=False, is_final=False)
        db.add(seg2)
        
        # Segment 3: Final Q&A (Final, Top 4)
        seg3 = Segment(event_id=event.id, name="Final Q&A", order_index=3, percentage_weight=0.40, is_active=False, is_final=True, qualifier_limit=4)
        db.add(seg3)
        db.commit()
        
        # Criteria
        db.add(Criteria(segment_id=seg1.id, name="Mastery", weight=0.50, max_score=100))
        db.add(Criteria(segment_id=seg1.id, name="Stage Presence", weight=0.50, max_score=100))
        db.add(Criteria(segment_id=seg2.id, name="Physical Fitness", weight=0.60, max_score=100))
        db.add(Criteria(segment_id=seg2.id, name="Poise", weight=0.40, max_score=100))
        db.add(Criteria(segment_id=seg3.id, name="Intelligence", weight=0.70, max_score=100))
        db.add(Criteria(segment_id=seg3.id, name="Confidence", weight=0.30, max_score=100))

        print("✅ Created Segments")

        # 5. Create Candidates (5 Male, 5 Female)
        candidates = [
            (1, "John Doe", "Male"), (2, "Michael Smith", "Male"), (3, "Robert Johnson", "Male"), (4, "David Williams", "Male"), (5, "James Brown", "Male"),
            (1, "Jane Doe", "Female"), (2, "Emily Davis", "Female"), (3, "Sarah Wilson", "Female"), (4, "Jessica Taylor", "Female"), (5, "Ashley Anderson", "Female"),
        ]

        for num, name, gender in candidates:
            c = Contestant(event_id=event.id, candidate_number=num, name=name, gender=gender, status="Active")
            db.add(c)
        
        db.commit()
        print(f"✅ Added {len(candidates)} Candidates")
        print("🚀 Seed Complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()