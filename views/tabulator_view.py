import flet as ft
import threading
import time
from services.quiz_service import QuizService
from services.event_service import EventService
from services.contestant_service import ContestantService
from core.database import SessionLocal
from models.all_models import Contestant, Segment, Score
from components.dialogs import show_about_dialog, show_contact_dialog

def TabulatorView(page: ft.Page, on_logout_callback):
    # Services
    quiz_service = QuizService()
    event_service = EventService()
    contestant_service = ContestantService()

    # State
    tabulator_id = page.session.get("user_id")
    tabulator_name = page.session.get("user_name")
    
    current_event = None
    active_round = None
    assigned_contestant = None
    
    # State tracking for Auto-Refresh
    last_round_id = None
    last_question_count = 0
    is_polling = True
    
    # Local cache to store selections before saving
    answers_cache = {} 
    
    # UI Containers
    main_container = ft.Container(expand=True, padding=20)
    score_list = ft.Column(scroll="adaptive", expand=True, spacing=10)

    # ---------------------------------------------------------
    # 1. HEADER (Matched to JudgeView)
    # ---------------------------------------------------------
    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.ASSIGNMENT, color="white"),
                ft.Column([
                    ft.Text(f"Tabulator: {tabulator_name}", color="white", weight="bold"),
                    ft.Text("Quiz Bee Panel", size=12, color="white70")
                ], spacing=2)
            ]),
            ft.Row([
                ft.TextButton("About", style=ft.ButtonStyle(color=ft.Colors.WHITE), on_click=lambda e: show_about_dialog(page)),
                ft.TextButton("Contact", style=ft.ButtonStyle(color=ft.Colors.WHITE), on_click=lambda e: show_contact_dialog(page)),
                ft.VerticalDivider(width=10, color="white24"),
                ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="white", tooltip="Log Out", on_click=lambda e: stop_and_logout(e))
            ])
        ], alignment="spaceBetween"),
        padding=15, 
        bgcolor=ft.Colors.BLUE_800
    )

    def stop_and_logout(e):
        nonlocal is_polling
        is_polling = False
        on_logout_callback(e)

    # ---------------------------------------------------------
    # 2. DATA LOADING & POLLING
    # ---------------------------------------------------------
    def load_dashboard():
        nonlocal current_event, active_round, assigned_contestant, last_round_id, last_question_count
        
        # Only show spinner on first load
        if not current_event:
            main_container.content = ft.ProgressRing()
            page.update()

        events = event_service.get_active_events("QuizBee")
        if not events:
            show_error("No Active Quiz Bee Event found."); return
        
        current_event = events[0] 

        active_round = event_service.get_active_segment(current_event.id)
        if not active_round:
            show_wait_screen("Waiting for Admin to start a round...", force_refresh=False)
            last_round_id = None
            return

        db = SessionLocal()
        assigned_contestant = db.query(Contestant).filter(
            Contestant.event_id == current_event.id,
            Contestant.assigned_tabulator_id == tabulator_id
        ).first()
        
        if not assigned_contestant:
            db.close(); show_error(f"You are not assigned to any school/participant in '{current_event.name}'."); return

        # Check Participation
        if active_round.participating_school_ids:
            allowed_ids = [int(x) for x in active_round.participating_school_ids.split(",") if x.strip()]
            if assigned_contestant.id not in allowed_ids:
                db.close()
                show_wait_screen(f"Your school ({assigned_contestant.name}) is not participating in: {active_round.name}", force_refresh=False)
                last_round_id = None # Reset state so we re-check later
                return

        db.close()

        # Check if UI update is needed (Round Changed or Questions Added)
        if active_round.id != last_round_id or active_round.total_questions != last_question_count:
            render_scoring_ui()
            last_round_id = active_round.id
            last_question_count = active_round.total_questions

    def poll_updates():
        while is_polling:
            if page:
                try:
                    load_dashboard()
                except: pass
            time.sleep(2)

    def show_error(msg):
        main_container.content = ft.Column([
            ft.Icon(ft.Icons.WARNING_AMBER, size=60, color="orange"),
            ft.Text(msg, size=18, text_align="center"),
            ft.ElevatedButton("Retry", on_click=lambda e: load_dashboard())
        ], alignment="center", horizontal_alignment="center")
        page.update()

    def show_wait_screen(msg, force_refresh=True):
        content = ft.Column([
            ft.Icon(ft.Icons.HOURGLASS_EMPTY, size=60, color="blue"),
            ft.Text("Please Wait", size=24, weight="bold"),
            ft.Text(msg, size=16, text_align="center", color="grey")
        ], alignment="center", horizontal_alignment="center")
        
        if force_refresh:
             content.controls.append(ft.OutlinedButton("Check for Updates", icon=ft.Icons.REFRESH, on_click=lambda e: load_dashboard()))
        
        main_container.content = content
        page.update()

    # ---------------------------------------------------------
    # 3. SCORING UI
    # ---------------------------------------------------------
    def render_scoring_ui():
        score_list.controls.clear()
        answers_cache.clear()
        
        info_card = ft.Container(padding=15, bgcolor=ft.Colors.BLUE_50, border_radius=10, content=ft.Row([
                ft.Column([ft.Text("Event", size=12, color="grey"), ft.Text(current_event.name, weight="bold")]),
                ft.Column([ft.Text("Current Round", size=12, color="grey"), ft.Text(active_round.name, weight="bold", color="blue")]),
                ft.Column([ft.Text("Assigned To", size=12, color="grey"), ft.Text(assigned_contestant.name, weight="bold", size=18, color="black")])
            ], alignment="spaceBetween"))

        total_qs = active_round.total_questions
        limit = total_qs if total_qs > 0 else 20 

        db = SessionLocal()
        existing_scores = db.query(Score).filter(Score.contestant_id == assigned_contestant.id, Score.segment_id == active_round.id).all()
        db.close()
        
        score_map = {s.question_number: s.is_correct for s in existing_scores}

        for i in range(1, limit + 1):
            q_num = i
            current_val = score_map.get(q_num, None)
            if current_val is not None: answers_cache[q_num] = current_val

            rg = ft.RadioGroup(content=ft.Row([ft.Radio(value="correct", label="Correct", fill_color="green"), ft.Radio(value="wrong", label="Wrong", fill_color="red")]), value="correct" if current_val is True else "wrong" if current_val is False else None, on_change=lambda e, q=q_num: update_cache(q, e.control.value))
            row = ft.Container(padding=10, bgcolor="white", border_radius=8, border=ft.border.all(1, ft.Colors.GREY_200), content=ft.Row([ft.Text(f"Q{q_num}", weight="bold", size=16, width=50), rg], alignment="spaceBetween"))
            score_list.controls.append(row)

        submit_btn = ft.ElevatedButton("Save & Submit Answers", icon=ft.Icons.SAVE, bgcolor=ft.Colors.GREEN, color="white", height=50, width=250, on_click=save_all_scores)

        main_container.content = ft.Column([info_card, ft.Divider(), ft.Text("Mark Answers:", weight="bold"), ft.Container(score_list, expand=True), ft.Container(content=submit_btn, alignment=ft.alignment.center, padding=10)], expand=True)
        page.update()

    def update_cache(q_num, value):
        answers_cache[q_num] = (value == "correct")

    def save_all_scores(e):
        if not answers_cache: page.open(ft.SnackBar(ft.Text("No answers marked yet."), bgcolor="orange")); return
        e.control.text = "Saving..."; e.control.disabled = True; page.update()
        errors = 0
        for q_num, is_correct in answers_cache.items():
            success, msg = quiz_service.submit_answer(tabulator_id, assigned_contestant.id, active_round.id, q_num, is_correct)
            if not success: errors += 1
        if errors > 0: page.open(ft.SnackBar(ft.Text(f"Saved with {errors} errors."), bgcolor="red"))
        else: page.open(ft.SnackBar(ft.Text("All scores saved successfully!"), bgcolor="green"))
        e.control.text = "Save & Submit Answers"; e.control.disabled = False; page.update()

    # Initial Load & Start Polling
    threading.Thread(target=poll_updates, daemon=True).start()

    return ft.Column([header, main_container], expand=True)