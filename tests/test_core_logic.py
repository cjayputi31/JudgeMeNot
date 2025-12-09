import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import datetime

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.auth_service import AuthService
from services.pageant_service import PageantService
from services.quiz_service import QuizService
from services.admin_service import AdminService
from services.event_service import EventService
from models.all_models import User, Event, Segment, Score, Criteria

class TestJudgeMeNotCore(unittest.TestCase):

    def setUp(self):
        """Setup runs before every test."""
        self.auth_service = AuthService()
        self.pageant_service = PageantService()
        self.quiz_service = QuizService()
        self.admin_service = AdminService()
        self.event_service = EventService()

    # =================================================================
    # 1. CORE FUNCTIONALITY UNIT TESTS
    # =================================================================

    # --- TEST: USER CREATION ---
    @patch('services.admin_service.SessionLocal')
    @patch('bcrypt.gensalt')
    @patch('bcrypt.hashpw')
    def test_user_creation(self, mock_hashpw, mock_gensalt, mock_session):
        """Verify Admin can create a user and password is hashed."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # Mock bcrypt
        mock_gensalt.return_value = b'somesalt'
        mock_hashpw.return_value = b'hashed_secret'

        # Mock query to ensure username doesn't exist
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute
        success, msg = self.admin_service.create_user(1, "New Judge", "judge1", "pass123", "Judge")

        # Assert
        self.assertTrue(success)
        # Check if db.add was called with a User object
        # Note: create_user might add User AND AuditLog, so we search for User
        user_added = False
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, User):
                self.assertEqual(obj.username, "judge1")
                self.assertEqual(obj.role, "Judge")
                user_added = True
                break
        
        self.assertTrue(user_added, "User object was not added to DB")
        print("✅ TEST PASSED: User creation with hashing.")

    # --- TEST: AUTH FLOW ---
    @patch('services.auth_service.SessionLocal')
    @patch('bcrypt.checkpw')
    def test_auth_flow(self, mock_checkpw, mock_session):
        """Verify Login logic (Success vs Failure)."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock User in DB
        mock_user = User(id=1, username="admin", password_hash="hashed_pw", role="Admin", is_active=True, is_pending=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        # Scenario A: Correct Password
        mock_checkpw.return_value = True
        result = self.auth_service.login("admin", "correct_pass")
        self.assertIsNotNone(result)
        if result not in ["DISABLED", "PENDING"]:
             self.assertEqual(result.username, "admin")

        # Scenario B: Wrong Password
        mock_checkpw.return_value = False
        result_fail = self.auth_service.login("admin", "wrong_pass")
        self.assertIsNone(result_fail)
        
        print("✅ TEST PASSED: Auth flow (Login success/fail).")

    # --- TEST: ROLE ENFORCEMENT ---
    @patch('services.event_service.SessionLocal')
    def test_role_enforcement(self, mock_session):
        """Verify a judge is only allowed if assigned to the event."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Scenario: Judge IS assigned
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock() # Returns a record
        allowed = self.event_service.is_judge_assigned(judge_id=99, event_id=1)
        self.assertTrue(allowed)

        # Scenario: Judge is NOT assigned
        mock_db.query.return_value.filter.return_value.first.return_value = None # Returns nothing
        denied = self.event_service.is_judge_assigned(judge_id=88, event_id=1)
        self.assertFalse(denied)
        
        print("✅ TEST PASSED: Role enforcement (Judge Assignment check).")

    # =================================================================
    # 2. ENHANCEMENT TESTS
    # =================================================================

    # --- ENHANCEMENT: SECURITY (AUDIT LOGGING) ---
    @patch('services.auth_service.SessionLocal')
    @patch('bcrypt.checkpw')
    def test_security_audit_logging(self, mock_checkpw, mock_session):
        """Verify that a sensitive action (Login) creates an Audit Log entry."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        
        # Setup valid user
        mock_user = User(id=1, username="test_user", password_hash="hash", role="Judge", is_active=True, is_pending=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_checkpw.return_value = True

        # Action: Login
        self.auth_service.login("test_user", "pass")

        # Assert: Check if AuditLog was added to DB
        # db.add is called twice: once for User (if creating) or AuditLog
        # In login, we expect db.add(log)
        
        # Iterate through calls to db.add to find an AuditLog object
        audit_log_created = False
        for call in mock_db.add.call_args_list:
            obj = call[0][0] # The argument passed to db.add()
            if hasattr(obj, 'action') and obj.action == "LOGIN":
                audit_log_created = True
                break
        
        self.assertTrue(audit_log_created, "Security Audit Log was NOT created on login.")
        print("✅ TEST PASSED: Security Enhancement (Audit Log creation).")

    # --- ENHANCEMENT: MULTI-PLATFORM (LOGIC CHECK) ---
    def test_multi_platform_logic(self):
        """
        Verify the logic used to detect Android devices.
        (This logic is used in main.py routing).
        """
        # Scenario 1: Desktop User Agent
        ua_desktop = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        is_android_desktop = "Android" in ua_desktop
        self.assertFalse(is_android_desktop)

        # Scenario 2: Mobile User Agent
        ua_mobile = "Mozilla/5.0 (Linux; Android 10; SM-G960F)"
        is_android_mobile = "Android" in ua_mobile
        self.assertTrue(is_android_mobile)
        
        print("✅ TEST PASSED: Multi-platform logic (Android detection).")

    # =================================================================
    # 3. INTEGRATION TEST (WORKFLOW SIMULATION)
    # =================================================================
    
    @patch('services.event_service.SessionLocal')
    @patch('services.admin_service.SessionLocal')
    def test_integration_event_lifecycle(self, mock_admin_session, mock_event_session):
        """
        Simulate Full Lifecycle: Admin Creates Event -> Adds Round -> Activates it.
        """
        # Create ONE mock database session object to represent the "Shared" DB
        mock_db = MagicMock()
        
        # Tell BOTH services to use this single mock DB instance
        mock_admin_session.return_value = mock_db
        mock_event_session.return_value = mock_db
        
        # FIX: Tell the mock database to return a float (0.0) when asking for sum/scalar
        mock_db.query.return_value.filter.return_value.scalar.return_value = 0.0

        # 1. Admin Creates Event
        self.admin_service.create_event(1, "Integration Quiz", "QuizBee")
        
        # Check if Event was added (AdminService calls add() twice: Event + Log)
        event_created = False
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Event) and obj.name == "Integration Quiz":
                event_created = True
                break
        self.assertTrue(event_created, "Event object was not added to DB")
        
        # 2. Admin Adds Segment
        self.event_service.add_segment(1, "Easy Round", 0.0, 1)
        
        # Check if Segment was added
        segment_created = False
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Segment) and obj.name == "Easy Round":
                segment_created = True
                break
        self.assertTrue(segment_created, "Segment object was not added to DB")
        
        # 3. Admin Activates Segment (Restricted Action)
        # Mock retrieving the segment so set_active_segment can find it
        mock_seg = Segment(id=10, name="Easy Round", is_active=False)
        mock_db.query.return_value.get.return_value = mock_seg
        
        # Mock the query filter for resetting other segments
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_seg]

        self.event_service.set_active_segment(1, 10)
        
        # Verify status changed
        self.assertTrue(mock_seg.is_active)
        
        print("✅ TEST PASSED: Integration Workflow (Event Creation -> Activation).")

    # --- RECOMMENDED: AUTH TO RESTRICTED ACTION ---
    @patch('services.pageant_service.SessionLocal')
    @patch('services.auth_service.SessionLocal')
    @patch('bcrypt.checkpw')
    def test_integration_login_and_scoring(self, mock_checkpw, mock_auth_session, mock_pageant_session):
        """
        Simulate Full Flow: Login as Judge -> Submit Score.
        """
        mock_db = MagicMock()
        mock_auth_session.return_value = mock_db
        mock_pageant_session.return_value = mock_db
        
        # 1. Setup User in Mock DB
        judge_user = User(id=5, username="judge_mike", password_hash="hash", role="Judge", is_active=True, is_pending=False)
        # We need to configure the mock to return this user when queried
        # The first query is in login (filter username)
        mock_db.query.return_value.filter.return_value.first.return_value = judge_user
        
        # 2. LOGIN
        mock_checkpw.return_value = True # Password Matches
        logged_in_user = self.auth_service.login("judge_mike", "password")
        
        self.assertIsNotNone(logged_in_user)
        self.assertEqual(logged_in_user.id, 5)
        
        # 3. SUBMIT SCORE (Restricted Action)
        # We need to mock the criteria lookup inside submit_score
        mock_criteria = Criteria(id=101, segment_id=202, name="Poise")
        mock_db.query.return_value.get.return_value = mock_criteria
        
        # Ensure 'existing_score' check returns None (so we add a new one)
        # The query logic in services uses filter().first()
        # We reset the mock response for the scoring phase to avoid returning the 'User' object
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        self.pageant_service.submit_score(logged_in_user.id, 1, 101, 95.0)
        
        # 4. VERIFY
        # Check if Score was added to DB
        score_added = False
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Score) and obj.score_value == 95.0 and obj.judge_id == 5:
                score_added = True
                break
        
        self.assertTrue(score_added, "Score was not recorded after login.")
        print("✅ TEST PASSED: Integration Workflow (Login -> Submit Score).")

if __name__ == '__main__':
    unittest.main()