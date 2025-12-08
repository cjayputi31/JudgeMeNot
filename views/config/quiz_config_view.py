import flet as ft
import threading
import time
from services.quiz_service import QuizService
from services.contestant_service import ContestantService
from services.admin_service import AdminService
from services.event_service import EventService
from core.database import SessionLocal
from models.all_models import Segment, Contestant, User, Score
from sqlalchemy import func

def QuizConfigView(page: ft.Page, event_id: int):
    # Services
    quiz_service = QuizService()
    contestant_service = ContestantService()
    admin_service = AdminService()
    event_service = EventService()

    # State
    current_admin_id = page.session.get("user_id")
    editing_round_id = None 
    editing_contestant_id = None 
    
    # Auto-Refresh State
    is_polling = False

    # ---------------------------------------------------------
    # 1. CONFIGURATION TAB (Rounds)
    # ---------------------------------------------------------
    q_order = ft.TextField(label="Round #", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    q_round_name = ft.TextField(label="Round Name (e.g. Easy)", width=300)
    q_points = ft.TextField(label="Pts/Question", width=140, keyboard_type=ft.KeyboardType.NUMBER)
    q_total_qs = ft.TextField(label="Total Qs", width=140, keyboard_type=ft.KeyboardType.NUMBER, hint_text="0 for unlimited")

    q_is_final = ft.Checkbox(label="Is Final Round?", value=False)
    q_qualifiers = ft.TextField(label="Qualifiers (Top N)", width=200, keyboard_type=ft.KeyboardType.NUMBER, visible=True)

    def on_final_check(e): pass
    q_is_final.on_change = on_final_check

    def save_round(e):
        if not q_order.value or not q_round_name.value:
            page.open(ft.SnackBar(ft.Text("Round # and Name are required"), bgcolor="red")); return
        try:
            order = int(q_order.value); pts = float(q_points.value) if q_points.value else 1.0
            qs = int(q_total_qs.value) if q_total_qs.value else 0; limit = int(q_qualifiers.value) if q_qualifiers.value else 0
            
            if editing_round_id:
                success, msg = quiz_service.update_round(current_admin_id, editing_round_id, q_round_name.value, pts, qs, order, q_is_final.value, limit)
            else:
                success, msg = quiz_service.add_round(current_admin_id, event_id, q_round_name.value, pts, qs, order, is_final=q_is_final.value, qualifier_limit=limit)
            
            if success:
                page.open(ft.SnackBar(ft.Text(f"Round {'Updated' if editing_round_id else 'Added'}!"), bgcolor="green"))
                page.close(round_dialog)
                q_order.value = str(order + 1); q_round_name.value = ""; q_points.value = ""; q_total_qs.value = ""; q_qualifiers.value = ""; q_is_final.value = False
                refresh_config_tab()
            else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError: page.open(ft.SnackBar(ft.Text("Invalid Number Input"), bgcolor="red"))
    round_dialog = ft.AlertDialog(
        title=ft.Text("Config Quiz Round"),
        content=ft.Column([ft.Row([q_order, q_round_name]), ft.Row([q_points, q_total_qs]), ft.Divider(), ft.Text("Elimination Rules", weight="bold", size=12), ft.Row([q_qualifiers, q_is_final])], height=320, width=450, tight=True),
        actions=[ft.TextButton("Save", on_click=save_round)]
    )

    def open_add_round_dialog(e): nonlocal editing_round_id; editing_round_id = None; q_order.value = ""; q_round_name.value = ""; q_points.value = ""; q_total_qs.value = ""; q_qualifiers.value = ""; q_is_final.value = False; round_dialog.title.value = "Add Quiz Round"; page.open(round_dialog)
    def open_edit_round_dialog(e): nonlocal editing_round_id; d = e.control.data; editing_round_id = d.id; q_order.value = str(d.order_index); q_round_name.value = d.name; q_points.value = str(int(d.points_per_question)); q_total_qs.value = str(d.total_questions); q_qualifiers.value = str(d.qualifier_limit); q_is_final.value = d.is_final; round_dialog.title.value = "Edit Quiz Round"; page.open(round_dialog)

    config_container = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def refresh_config_tab():
        config_container.controls.clear()
        config_container.controls.append(ft.Row([ft.Text("Quiz Rounds Sequence", size=20, weight="bold"), ft.ElevatedButton("Add Round", icon=ft.Icons.ADD, on_click=open_add_round_dialog)], alignment="spaceBetween"))

        db = SessionLocal()
        rounds = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        db.close()

        if not rounds:
            config_container.controls.append(ft.Text("No rounds configured yet.", italic=True, color="grey"))

        for r in rounds:
            badges = [ft.Chip(label=ft.Text(f"{int(r.points_per_question)} pts/each"), bgcolor=ft.Colors.BLUE_50)]
            if r.qualifier_limit > 0: badges.append(ft.Chip(label=ft.Text(f"Top {r.qualifier_limit} Advance"), bgcolor=ft.Colors.ORANGE_100))
            if r.is_final: badges.append(ft.Container(content=ft.Text("FINAL ROUND", color="white", weight="bold", size=10), bgcolor="red", padding=5, border_radius=5))

            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Row([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"#{r.order_index}", size=20, weight="bold", color="white"),
                                bgcolor="black", width=40, height=40, border_radius=20, alignment=ft.alignment.center
                            ),
                            ft.Column([
                                ft.Text(f"{r.name}", size=18, weight="bold"),
                                ft.Row(badges)
                            ])
                        ]),

                        ft.Row([
                            ft.IconButton(icon=ft.Icons.EDIT, tooltip="Edit Round", data=r, on_click=open_edit_round_dialog),
                            # Note: Activation logic is also available in Mission Control (Tabulation Tab)
                        ])
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            config_container.controls.append(card)
        
        config_container.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, color="blue"),
                    ft.Text("Note: Clincher rounds will be triggered automatically if ties occur at the qualifying limit.", size=12, italic=True)
                ]),
                padding=10, bgcolor=ft.Colors.BLUE_50, border_radius=5
            )
        )
        page.update()

    def toggle_round_active(seg_id, is_active):
        if is_active: success, msg = event_service.set_active_segment(event_id, seg_id)
        else: success, msg = event_service.set_active_segment(event_id, None)
        if success: page.open(ft.SnackBar(ft.Text(msg), bgcolor="green")); refresh_config_tab()
        else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    # ---------------------------------------------------------
    # 2. CONTESTANTS TAB
    # ---------------------------------------------------------
    c_number = ft.TextField(label="School/Team #", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    c_name = ft.TextField(label="School/Participant Name", width=300)
    c_tabulator = ft.Dropdown(label="Assign Tabulator", width=300) 
    contestant_container = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def load_tabulators(current_assigned_id=None):
        db = SessionLocal()
        all_tabulators = db.query(User).filter(User.role == "Tabulator").all()
        assignments = db.query(Contestant.assigned_tabulator_id).filter(Contestant.event_id == event_id, Contestant.assigned_tabulator_id.isnot(None)).all()
        assigned_ids = [a[0] for a in assignments]
        db.close()
        options = [ft.dropdown.Option(key="", text="-- Unassigned --")]
        for t in all_tabulators:
            if t.id not in assigned_ids or t.id == current_assigned_id: options.append(ft.dropdown.Option(key=str(t.id), text=t.name))
        c_tabulator.options = options

    def save_contestant(e):
        if not c_number.value or not c_name.value: page.open(ft.SnackBar(ft.Text("Please fill required fields"), bgcolor="red")); return
        try:
            num = int(c_number.value); tab_id = int(c_tabulator.value) if c_tabulator.value else None
            if editing_contestant_id:
                success, msg = contestant_service.update_contestant(editing_contestant_id, num, c_name.value, "Mixed")
                if success: update_tabulator_link(editing_contestant_id, tab_id)
            else:
                success, msg = contestant_service.add_contestant(event_id, num, c_name.value, "Mixed")
                if success: update_tabulator_link_by_num(num, tab_id)
            if success: page.open(ft.SnackBar(ft.Text(f"Participant {'Updated' if editing_contestant_id else 'Added'}!"), bgcolor="green")); page.close(add_c_dialog); refresh_contestant_tab()
            else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError: page.open(ft.SnackBar(ft.Text("Invalid Input"), bgcolor="red"))

    def update_tabulator_link(cid, tid): 
        db = SessionLocal(); c = db.query(Contestant).get(cid)
        if c: c.assigned_tabulator_id = tid; db.commit()
        db.close()
    def update_tabulator_link_by_num(num, tid):
        db = SessionLocal(); c = db.query(Contestant).filter(Contestant.event_id == event_id, Contestant.candidate_number == num).first()
        if c: c.assigned_tabulator_id = tid; db.commit()
        db.close()

    add_c_dialog = ft.AlertDialog(title=ft.Text("Add Participant"), content=ft.Column([c_number, c_name, c_tabulator], height=250, width=400, tight=True), actions=[ft.TextButton("Save", on_click=save_contestant)])
    def open_add_c_dialog(e): nonlocal editing_contestant_id; editing_contestant_id = None; c_number.value = ""; c_name.value = ""; load_tabulators(None); c_tabulator.value = ""; add_c_dialog.title.value = "Add Participant"; page.open(add_c_dialog)
    def open_edit_c_dialog(e): nonlocal editing_contestant_id; d = e.control.data; editing_contestant_id = d.id; c_number.value = str(d.candidate_number); c_name.value = d.name; load_tabulators(d.assigned_tabulator_id); c_tabulator.value = str(d.assigned_tabulator_id) if d.assigned_tabulator_id else ""; add_c_dialog.title.value = "Edit Participant"; page.open(add_c_dialog)
    def delete_contestant(cid): contestant_service.delete_contestant(cid); refresh_contestant_tab()

    def refresh_contestant_tab():
        contestant_container.controls.clear()
        contestant_container.controls.append(ft.Row([ft.Text("Participants & Tabulators", size=20, weight="bold"), ft.ElevatedButton("Add Participant", icon=ft.Icons.ADD, on_click=open_add_c_dialog)], alignment="spaceBetween"))
        db = SessionLocal(); participants = db.query(Contestant).outerjoin(User, Contestant.assigned_tabulator_id == User.id).filter(Contestant.event_id == event_id).order_by(Contestant.candidate_number).all()
        rows = []
        for p in participants:
            tab_name = "Unassigned"
            if p.assigned_tabulator_id: t_user = db.query(User).get(p.assigned_tabulator_id); tab_name = t_user.name if t_user else "Unknown"
            rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(p.candidate_number), weight="bold")), ft.DataCell(ft.Text(p.name)), ft.DataCell(ft.Container(content=ft.Text(tab_name, size=12, color="white"), bgcolor="orange" if tab_name == "Unassigned" else "blue", padding=5, border_radius=5)), ft.DataCell(ft.Row([ft.IconButton(icon=ft.Icons.EDIT, icon_color="blue", tooltip="Edit", data=p, on_click=open_edit_c_dialog), ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", tooltip="Delete", data=p.id, on_click=lambda e: delete_contestant(e.control.data))]))]))
        db.close()

        contestant_container.controls.append(ft.DataTable(columns=[ft.DataColumn(ft.Text("#")), ft.DataColumn(ft.Text("Participant / School")), ft.DataColumn(ft.Text("Assigned Tabulator")), ft.DataColumn(ft.Text("Action"))], rows=rows, border=ft.border.all(1, "grey"), heading_row_color=ft.Colors.BLUE_50, width=float("inf"))); page.update()

    # ---------------------------------------------------------
    # 3. MISSION CONTROL (TABULATION)
    # ---------------------------------------------------------
    tabulation_container = ft.Container(expand=True)

    def toggle_round_from_control(seg_id):
        active_seg = event_service.get_active_segment(event_id)
        if active_seg and active_seg.id == seg_id: success, msg = event_service.set_active_segment(event_id, None)
        else: success, msg = event_service.set_active_segment(event_id, seg_id)
        if success: page.open(ft.SnackBar(ft.Text(msg), bgcolor="green" if active_seg and active_seg.id != seg_id else "orange")); refresh_tabulation_tab()
        else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    def add_clincher_question(seg_id):
        db = SessionLocal()
        seg = db.query(Segment).get(seg_id)
        if seg:
            seg.total_questions += 1
            db.commit()
            page.open(ft.SnackBar(ft.Text(f"Clincher Updated! Now {seg.total_questions} Questions"), bgcolor="green"))
            refresh_tabulation_tab()
        db.close()

    def refresh_tabulation_tab():
        db = SessionLocal()
        rounds = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        left_controls = []
        active_seg = None
        is_clincher_active = False
        
        for r in rounds:
            is_active = r.is_active
            if is_active: 
                active_seg = r
                if "Clincher" in r.name: is_clincher_active = True
            
            card_bg = ft.Colors.BLUE_600 if is_active else ft.Colors.WHITE
            text_col = ft.Colors.WHITE if is_active else ft.Colors.BLACK
            sub_col = ft.Colors.WHITE70 if is_active else ft.Colors.GREY
            btn_text = "STOP" if is_active else "START"
            btn_fg = ft.Colors.RED if is_active else ft.Colors.GREEN
            
            if "Clincher" in r.name and is_active:
                action_btn = ft.ElevatedButton("+1 Question", icon=ft.Icons.ADD_CIRCLE, color="white", bgcolor="orange", width=120, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)), data=r.id, on_click=lambda e: add_clincher_question(e.control.data))
                stop_btn = ft.IconButton(icon=ft.Icons.STOP_CIRCLE, icon_color="red", tooltip="Stop Round", data=r.id, on_click=lambda e: toggle_round_from_control(e.control.data))
                action_area = ft.Row([action_btn, stop_btn], spacing=5)
            else:
                action_area = ft.ElevatedButton(btn_text, color=btn_fg, bgcolor=ft.Colors.WHITE, width=80, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)), data=r.id, on_click=lambda e: toggle_round_from_control(e.control.data))

            left_controls.append(ft.Container(bgcolor=card_bg, border=ft.border.all(1, ft.Colors.GREY_300) if not is_active else None, border_radius=8, padding=10, content=ft.Row([ft.Column([ft.Text(r.name, weight="bold", color=text_col, size=16), ft.Text(f"{r.total_questions} Qs | {int(r.points_per_question)} Pts", size=12, color=sub_col)]), action_area], alignment="spaceBetween")))
        
        left_column = ft.Container(width=380, bgcolor=ft.Colors.GREY_50, padding=10, border_radius=10, content=ft.Column([ft.Text("Mission Control", size=20, weight="bold"), ft.Text(f"Event ID: {event_id}", size=12, color="grey"), ft.Divider(), ft.Column(left_controls, scroll="auto", expand=True)]))

        header_bg = ft.Colors.RED_900 if active_seg else ft.Colors.BLUE_GREY_700
        header_text = f"LIVE: {active_seg.name}" if active_seg else "NO ACTIVE ROUND"
        badges = []
        if active_seg:
            if active_seg.qualifier_limit > 0: badges.append(ft.Container(content=ft.Text(f"Top {active_seg.qualifier_limit} Advance", size=10, weight="bold"), bgcolor="white", padding=5, border_radius=10))
            if is_clincher_active: badges.append(ft.Container(content=ft.Text("Clincher Mode: Separate Scores", size=10, weight="bold"), bgcolor="purple", padding=5, border_radius=10))
            else: badges.append(ft.Container(content=ft.Text("Cumulative", size=10, weight="bold"), bgcolor="orange", padding=5, border_radius=10))

        right_header = ft.Container(bgcolor=header_bg, padding=10, border_radius=ft.border_radius.only(top_left=10, top_right=10), content=ft.Row([ft.Row([ft.Icon(ft.Icons.FIBER_MANUAL_RECORD, color="red" if active_seg else "grey"), ft.Text(header_text, color="white", weight="bold", size=18), ft.Row(badges)]), ft.Container()], alignment="spaceBetween"))

        # Fetch Data
        if is_clincher_active and active_seg:
            results = quiz_service.get_live_scores(event_id, specific_round_id=active_seg.id)
            if active_seg.participating_school_ids:
                p_ids = [int(x) for x in active_seg.participating_school_ids.split(",") if x.strip()]
                results = [r for r in results if r['contestant_id'] in p_ids]
        else:
            results = quiz_service.get_live_scores(event_id)

        active_limit = active_seg.qualifier_limit if active_seg else 0

        rows = []
        for i, res in enumerate(results):
            rank = i + 1

            row_bg = "white"
            progress_text = "-"
            if active_seg:
                ans_count = db.query(Score).filter(Score.contestant_id == res['contestant_id'], Score.segment_id == active_seg.id).count()
                progress_text = f"{ans_count}/{active_seg.total_questions}"
            
            if active_limit > 0:
                if rank <= active_limit: row_bg = ft.Colors.GREEN_50
            
            rows.append(ft.DataRow(color=row_bg, cells=[ft.DataCell(ft.Text(str(rank), weight="bold")), ft.DataCell(ft.Text(res['name'], weight="bold")), ft.DataCell(ft.Container(content=ft.Text(progress_text, color="white", size=12), bgcolor="green" if progress_text != "-" else "grey", padding=5, border_radius=10)), ft.DataCell(ft.Text(str(res['total_score']), weight="bold", size=16))]))

        right_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Rank", weight="bold")), ft.DataColumn(ft.Text("School", weight="bold")), ft.DataColumn(ft.Text("Progress", weight="bold")), ft.DataColumn(ft.Text("Score", weight="bold"), numeric=True)], rows=rows, border=ft.border.all(1, "grey"), heading_row_color=ft.Colors.GREY_200, width=float("inf"))

        eval_box = ft.Container(padding=20, bgcolor=ft.Colors.GREEN_50, border_radius=10, border=ft.border.all(1, "green"), content=ft.Column([ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color="green"), ft.Text("Round Evaluation", weight="bold")]), ft.Text("Round Complete? Evaluate to update rankings or create clinchers.", size=12), ft.ElevatedButton("Evaluate", bgcolor="green", color="white", width=float("inf"), on_click=lambda e: evaluate_round())]))

        right_content = ft.Container(expand=True, content=ft.Column([right_header, ft.Container(content=ft.Column([right_table], scroll="adaptive", expand=True), expand=True, padding=10), eval_box]))
        db.close()
        tabulation_container.content = ft.Row([left_column, ft.VerticalDivider(width=1), right_content], expand=True)
        page.update()

    # --- AUTO REFRESH LOGIC ---
    def poll_updates():
        while is_polling:
            # We check if page is still valid (not closed)
            if page:
                try:
                    # We can't update UI directly from thread, so we schedule it
                    # But calling refresh_tabulation_tab directly rebuilds UI which is heavy.
                    # Ideally, we check for changes (version number or active status) then update.
                    # For simplicity, we just rebuild if the Tab is visible.
                    # Assuming we can check if tab 2 is selected.
                    # This might cause flicker, but fulfils "auto refresh" req.
                    refresh_tabulation_tab()
                except:
                    break
            time.sleep(3) # Update every 3 seconds

    def evaluate_round():
        active_seg = event_service.get_active_segment(event_id)
        if not active_seg: page.open(ft.SnackBar(ft.Text("No active round to evaluate."), bgcolor="red")); return
        limit = active_seg.qualifier_limit
        if limit <= 0: page.open(ft.SnackBar(ft.Text("This round has no qualifier limit."), bgcolor="grey")); return

        is_clincher = "Clincher" in active_seg.name
        if is_clincher:
             results = quiz_service.get_live_scores(event_id, specific_round_id=active_seg.id)
             if active_seg.participating_school_ids:
                p_ids = [int(x) for x in active_seg.participating_school_ids.split(",") if x.strip()]
                results = [r for r in results if r['contestant_id'] in p_ids]
        else:
            results = quiz_service.get_live_scores(event_id)

        if len(results) <= limit: page.open(ft.SnackBar(ft.Text("All participants qualify."), bgcolor="green")); return

        last_in_score = results[limit-1]['total_score']
        first_out_score = results[limit]['total_score']

        if last_in_score == first_out_score:
            tied_participants = [r for r in results if r['total_score'] == last_in_score]
            people_above = len([r for r in results if r['total_score'] > last_in_score])
            spots_available = limit - people_above
            
            tie_dialog = ft.AlertDialog(title=ft.Text("TIE DETECTED!", color="red"), content=ft.Column([ft.Text(f"Tie score: {last_in_score}"), ft.Text(f"Spots available for tied group: {spots_available}"), ft.Text("Participants involved:", weight="bold"), ft.Column([ft.Text(f"• {p['name']}") for p in tied_participants])], tight=True), actions=[ft.TextButton("Ignore", on_click=lambda e: page.close(tie_dialog)), ft.ElevatedButton("Create Clincher", bgcolor="red", color="white", on_click=lambda e: (page.close(tie_dialog), trigger_clincher(tied_participants, active_seg, spots_available)))])
            page.open(tie_dialog)
        else:
            page.open(ft.SnackBar(ft.Text(f"No ties. Top {limit} advanced."), bgcolor="green"))

    def trigger_clincher(tied, active_round, spots_available):
        db = SessionLocal()
        last_round = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index.desc()).first()
        new_order = (last_round.order_index + 1) if last_round else 1
        tied_ids = [p['contestant_id'] for p in tied]
        success, msg = quiz_service.add_round(current_admin_id, event_id, f"Clincher ({active_round.name})", points=1, total_questions=1, order=new_order, is_final=False, qualifier_limit=spots_available, participating_ids=tied_ids)
        if success:
            page.open(ft.SnackBar(ft.Text(f"Clincher created for {len(tied)} participants!"), bgcolor="orange"))
            refresh_tabulation_tab()
        db.close()

    # ---------------------------------------------------------
    # MAIN ASSEMBLY
    # ---------------------------------------------------------
    main_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Configuration", icon=ft.Icons.SETTINGS, content=config_container),
            ft.Tab(text="Participants", icon=ft.Icons.PEOPLE, content=contestant_container),
            ft.Tab(text="Mission Control", icon=ft.Icons.DASHBOARD, content=tabulation_container),
        ],
        on_change=lambda e: load_current_tab(e.control.selected_index),
        expand=True
    )

    def load_current_tab(index):
        nonlocal is_polling
        # Start Polling only on Mission Control
        if index == 2:
            is_polling = True
            threading.Thread(target=poll_updates, daemon=True).start()
            refresh_tabulation_tab()
        else:
            is_polling = False # Stop polling on other tabs
            if index == 0: refresh_config_tab()
            elif index == 1: refresh_contestant_tab()

    refresh_config_tab()

    return ft.Container(content=main_tabs, padding=10, expand=True)   