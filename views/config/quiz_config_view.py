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
        try:
            order = int(q_order.value); pts = float(q_points.value) if q_points.value else 1.0
            qs = int(q_total_qs.value) if q_total_qs.value else 0; limit = int(q_qualifiers.value) if q_qualifiers.value else 0
            if editing_round_id: success, msg = quiz_service.update_round(current_admin_id, editing_round_id, q_round_name.value, pts, qs, order, q_is_final.value, limit)
            else: success, msg = quiz_service.add_round(current_admin_id, event_id, q_round_name.value, pts, qs, order, is_final=q_is_final.value, qualifier_limit=limit)
            if success:
                page.open(ft.SnackBar(ft.Text("Saved!"), bgcolor="green")); page.close(round_dialog)
                q_order.value = str(order + 1); q_round_name.value = ""; refresh_config_tab()
            else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except: page.open(ft.SnackBar(ft.Text("Invalid Input"), bgcolor="red"))

    # DELETE LOGIC
    def delete_round(round_id):
        def confirm_delete(e):
            page.close(del_dlg)
            success, msg = quiz_service.delete_round(current_admin_id, round_id)
            if success:
                page.open(ft.SnackBar(ft.Text("Round Deleted"), bgcolor="orange"))
                refresh_config_tab()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

        del_dlg = ft.AlertDialog(
            title=ft.Text("Delete Round?"),
            content=ft.Text("This will also delete ALL scores associated with this round. Are you sure?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(del_dlg)),
                ft.ElevatedButton("Delete", bgcolor="red", color="white", on_click=confirm_delete)
            ]
        )
        page.open(del_dlg)

    round_dialog = ft.AlertDialog(
        title=ft.Text("Config Quiz Round"),
        content=ft.Column([ft.Row([q_order, q_round_name]), ft.Row([q_points, q_total_qs]), ft.Divider(), ft.Text("Rules"), ft.Row([q_qualifiers, q_is_final])], height=320, width=450, tight=True),
        actions=[ft.TextButton("Save", on_click=save_round)]
    )

    def open_add_round_dialog(e): nonlocal editing_round_id; editing_round_id = None; q_order.value = ""; q_round_name.value = ""; q_points.value = ""; q_total_qs.value = ""; q_qualifiers.value = ""; q_is_final.value = False; round_dialog.title.value = "Add Quiz Round"; page.open(round_dialog)
    def open_edit_round_dialog(e): nonlocal editing_round_id; d = e.control.data; editing_round_id = d.id; q_order.value = str(d.order_index); q_round_name.value = d.name; q_points.value = str(int(d.points_per_question)); q_total_qs.value = str(d.total_questions); q_qualifiers.value = str(d.qualifier_limit); q_is_final.value = d.is_final; round_dialog.title.value = "Edit Quiz Round"; page.open(round_dialog)

    config_container = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def refresh_config_tab():
        config_container.controls.clear()
        config_container.controls.append(ft.Row([ft.Text("Quiz Rounds Sequence", size=20, weight="bold"), ft.ElevatedButton("Add Round", icon=ft.Icons.ADD, on_click=open_add_round_dialog)], alignment="spaceBetween"))
        db = SessionLocal(); rounds = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all(); db.close()
        for r in rounds:
            card = ft.Card(content=ft.Container(padding=10, content=ft.Row([ft.Row([ft.Container(content=ft.Text(f"#{r.order_index}", color="white", weight="bold"), bgcolor="black", padding=10, border_radius=20), ft.Column([ft.Text(r.name, weight="bold"), ft.Text(f"Qualifiers: {r.qualifier_limit}")])]), ft.Row([ft.IconButton(icon=ft.Icons.EDIT, icon_color="blue", tooltip="Edit", data=r, on_click=open_edit_round_dialog), ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", tooltip="Delete", data=r.id, on_click=lambda e: delete_round(e.control.data)), ft.Switch(value=r.is_active, on_change=lambda e, s=r.id: toggle_round_active(s, e.control.value))])], alignment="spaceBetween")))
            config_container.controls.append(card)
        page.update()
    
    def toggle_round_active(seg_id, is_active):
        if is_active: event_service.set_active_segment(event_id, seg_id)
        else: event_service.set_active_segment(event_id, None)
        refresh_config_tab()

    # ---------------------------------------------------------
    # 2. CONTESTANTS TAB
    # ---------------------------------------------------------
    c_number = ft.TextField(label="#", width=80); c_name = ft.TextField(label="Name", width=250); c_tab = ft.Dropdown(label="Tabulator", width=250)
    contestant_container = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def load_tabs(cur_id=None): db=SessionLocal(); ts=db.query(User).filter(User.role=="Tabulator").all(); db.close(); c_tab.options=[ft.dropdown.Option(str(t.id), t.name) for t in ts]
    def save_c(e): 
        try: 
            if editing_contestant_id: contestant_service.update_contestant(editing_contestant_id, int(c_number.value), c_name.value, "Mixed")
            else: contestant_service.add_contestant(event_id, int(c_number.value), c_name.value, "Mixed")
            # Link logic omitted for brevity
            page.close(c_dialog); refresh_c_tab()
        except: pass
    c_dialog = ft.AlertDialog(title=ft.Text("Contestant"), content=ft.Column([c_number, c_name, c_tab], height=200), actions=[ft.TextButton("Save", on_click=save_c)])
    def open_add_c_dialog(e): nonlocal editing_contestant_id; editing_contestant_id = None; c_number.value = ""; c_name.value = ""; load_tabs(); page.open(c_dialog)
    def open_edit_c_dialog(e): nonlocal editing_contestant_id; d = e.control.data; editing_contestant_id = d.id; c_number.value = str(d.candidate_number); c_name.value = d.name; load_tabs(); page.open(c_dialog)
    def delete_contestant(cid): contestant_service.delete_contestant(cid); refresh_contestant_tab()
    def refresh_c_tab(): refresh_contestant_tab() # Alias
    def refresh_contestant_tab():
        contestant_container.controls.clear()
        contestant_container.controls.append(ft.Row([ft.Text("Participants", size=20, weight="bold"), ft.ElevatedButton("Add", icon=ft.Icons.ADD, on_click=open_add_c_dialog)], alignment="spaceBetween"))
        db=SessionLocal(); cs=db.query(Contestant).filter(Contestant.event_id==event_id).all(); db.close()
        for c in cs:
            contestant_container.controls.append(ft.Container(padding=10, bgcolor=ft.Colors.GREY_50, content=ft.Row([ft.Text(f"#{c.candidate_number} {c.name}"), ft.IconButton(icon=ft.Icons.EDIT, data=c, on_click=open_edit_c_dialog), ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", data=c.id, on_click=lambda e: delete_contestant(e.control.data))])))
        page.update()

    # ---------------------------------------------------------
    # 3. MISSION CONTROL (Tabulation)
    # ---------------------------------------------------------
    tabulation_container = ft.Container(expand=True)
    def refresh_tabulation_tab():
        db = SessionLocal()
        active_seg = event_service.get_active_segment(event_id)

        # Left Panel (Round Controls)
        left_controls = []
        rounds = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        for r in rounds:
            is_active = (active_seg and active_seg.id == r.id)
            btn_text = "STOP" if is_active else "START"
            btn_col = ft.Colors.RED if is_active else ft.Colors.GREEN

            # Clincher +1 Button Logic
            if "Clincher" in r.name and is_active:
                action_area = ft.Row([
                    ft.ElevatedButton("+1 Q", bgcolor="orange", color="white", width=60, data=r.id, on_click=lambda e: add_clincher_question(e.control.data)),
                    ft.IconButton(icon=ft.Icons.STOP_CIRCLE, icon_color="red", data=r.id, on_click=lambda e: toggle_round_from_control(e.control.data))
                ], spacing=2)
            else:
                action_area = ft.ElevatedButton(btn_text, bgcolor="white", color=btn_col, width=80, data=r.id, on_click=lambda e: toggle_round_from_control(e.control.data))

            left_controls.append(ft.Container(bgcolor=ft.Colors.BLUE_600 if is_active else "white", border_radius=8, padding=10, border=ft.border.all(1, "grey") if not is_active else None, content=ft.Row([ft.Column([ft.Text(r.name, color="white" if is_active else "black", weight="bold"), ft.Text(f"{r.total_questions} Qs", color="white70" if is_active else "grey", size=12)]), action_area], alignment="spaceBetween")))
        
        # Right Panel (Live Stats)
        results = []
        is_clincher = active_seg and "Clincher" in active_seg.name

        if active_seg:
            # If Clincher, fetch specific round. If Normal, fetch cumulative.
            results = quiz_service.get_live_scores(event_id, specific_round_id=active_seg.id if is_clincher else None)
            
            # Filtering for Clincher Display:
            # Only show those who are 'invited' to this clincher
            if is_clincher and active_seg.participating_school_ids:
                p_ids = [int(x) for x in active_seg.participating_school_ids.split(",") if x.strip()]
                results = [r for r in results if r['contestant_id'] in p_ids]
        else:
            results = quiz_service.get_live_scores(event_id)
        
        rows = []
        limit = active_seg.qualifier_limit if active_seg else 0
        for i, res in enumerate(results):
            rank = i+1
            color = ft.Colors.GREEN_50 if limit > 0 and rank <= limit else "white"
            rows.append(ft.DataRow(color=color, cells=[ft.DataCell(ft.Text(str(rank))), ft.DataCell(ft.Text(res['name'])), ft.DataCell(ft.Text(str(res['total_score']), weight="bold"))]))

        table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Rank")), ft.DataColumn(ft.Text("Name")), ft.DataColumn(ft.Text("Score"))], rows=rows, border=ft.border.all(1, "grey"), width=float("inf"))
        
        eval_btn = ft.ElevatedButton("Evaluate", bgcolor="green", color="white", width=float("inf"), on_click=lambda e: evaluate_round())    

        tabulation_container.content = ft.Row([
            ft.Container(content=ft.Column([ft.Text("Rounds", weight="bold"), ft.Column(left_controls, scroll="auto", expand=True)], expand=True), width=300, bgcolor=ft.Colors.GREY_50, padding=10),
            ft.VerticalDivider(),
            ft.Container(content=ft.Column([ft.Text(f"LIVE: {active_seg.name if active_seg else 'None'}", size=20, weight="bold"), table, ft.Container(eval_btn, padding=10)], expand=True), expand=True)
        ], expand=True)
        db.close()

        page.update()

    def toggle_round_from_control(seg_id):
        active_seg = event_service.get_active_segment(event_id)
        if active_seg and active_seg.id == seg_id: event_service.set_active_segment(event_id, None)
        else: event_service.set_active_segment(event_id, seg_id)
        refresh_tabulation_tab()

    def add_clincher_question(seg_id):
        db = SessionLocal(); seg = db.query(Segment).get(seg_id)
        if seg: seg.total_questions += 1; db.commit(); page.open(ft.SnackBar(ft.Text("Question Added!"), bgcolor="green")); refresh_tabulation_tab()
        db.close()

    def evaluate_round():
        active_seg = event_service.get_active_segment(event_id)
        if not active_seg: return
        limit = active_seg.qualifier_limit
        if limit <= 0: page.open(ft.SnackBar(ft.Text("No limit set."), bgcolor="grey")); return

        is_clincher = "Clincher" in active_seg.name
        results = quiz_service.get_live_scores(event_id, specific_round_id=active_seg.id if is_clincher else None)
        
        if is_clincher:
             db = SessionLocal()
             if active_seg.participating_school_ids:
                 p_ids = [int(x) for x in active_seg.participating_school_ids.split(",") if x.strip()]
                 results = [r for r in results if r['contestant_id'] in p_ids]
             db.close()

        if len(results) <= limit: 
            page.open(ft.SnackBar(ft.Text("Participants <= Limit. Everyone qualifies."), bgcolor="green")); return

        last_in_score = results[limit-1]['total_score']
        first_out_score = results[limit]['total_score']

        if last_in_score == first_out_score:
            tied = [r for r in results if r['total_score'] == last_in_score]
            # Identify Clean Winners (those strictly above the tie)
            clean_winners = [r for r in results if r['total_score'] > last_in_score]
            spots = limit - len(clean_winners)
            dlg = ft.AlertDialog(
                title=ft.Text("Tie!"), 
                content=ft.Text(f"{len(tied)} tied for {spots} spots.\nClean Winners: {len(clean_winners)} (Will auto-advance)"), 
                actions=[ft.ElevatedButton("Create Clincher", on_click=lambda e: (page.close(dlg), trigger_clincher(tied, clean_winners, active_seg, spots)))]
            )
            page.open(dlg)
        else:
            qualifiers = results[:limit]
            adv_dlg = ft.AlertDialog(
                title=ft.Text("Results"), 
                content=ft.Column([ft.Text(f"Top {limit} Advance."), ft.Column([ft.Text(f"{q['name']}") for q in qualifiers], height=100, scroll="auto")], tight=True),
                actions=[ft.ElevatedButton("Advance Round", on_click=lambda e: (page.close(adv_dlg), perform_advance(active_seg.id, [q['contestant_id'] for q in qualifiers])))]
            )
            page.open(adv_dlg)
                
    
    def perform_advance(current_round_id, qual_ids):
        success, msg = quiz_service.advance_to_next_round(current_admin_id, event_id, current_round_id, qual_ids)
        if success: page.open(ft.SnackBar(ft.Text(msg), bgcolor="green")); refresh_tabulation_tab()
        else: page.open(ft.SnackBar(ft.Text(msg), bgcolor="red"))

    def trigger_clincher(tied, clean_winners, active_round, spots):
        db = SessionLocal()
        last_round = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index.desc()).first()
        new_order = (last_round.order_index + 1) if last_round else 1
        
        tied_ids = [p['contestant_id'] for p in tied]
        # Link to parent if this is a sub-clincher, or if active_round IS the parent
        parent_id = active_round.related_segment_id if active_round.related_segment_id else active_round.id
        
        success, msg = quiz_service.add_round(
            current_admin_id, event_id, f"Clincher ({active_round.name})", 
            points=1, total_questions=1, order=new_order, 
            is_final=False, qualifier_limit=spots, 
            participating_ids=tied_ids, related_id=parent_id
        )
        
        if success:
            # PRE-SEED CLEAN WINNERS TO NEXT ROUND
            if clean_winners:
                clean_ids = [p['contestant_id'] for p in clean_winners]
                # Find Next Normal Round
                next_round = db.query(Segment).filter(
                    Segment.event_id == event_id,
                    Segment.order_index > active_round.order_index,
                    Segment.related_segment_id == None # Find next independent round
                ).order_by(Segment.order_index).first()
                
                if next_round:
                    # Append Clean IDs to it
                    existing_ids = []
                    if next_round.participating_school_ids:
                        existing_ids = [int(x) for x in next_round.participating_school_ids.split(",") if x.strip()]
                    
                    final_ids = list(set(existing_ids + clean_ids))
                    next_round.participating_school_ids = ",".join(map(str, final_ids))
                    db.commit()
                    page.open(ft.SnackBar(ft.Text(f"Clincher Started! {len(clean_winners)} clean winners pre-advanced."), bgcolor="orange"))

            # Init scores for tied
            new_seg = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.id.desc()).first()
            for p in tied: db.add(Score(contestant_id=p['contestant_id'], segment_id=new_seg.id, judge_id=current_admin_id, question_number=0, score_value=0, is_correct=False))
            db.commit()
            refresh_tabulation_tab()
        
        db.close()
    def poll_updates():
        while is_polling:
            if page: 
                try: refresh_tabulation_tab()
                except: break
            time.sleep(3)

    main_tabs = ft.Tabs(
        tabs=[ft.Tab(text="Config", content=config_container), ft.Tab(text="Contestants", content=contestant_container), ft.Tab(text="Mission Control", content=tabulation_container)],
        on_change=lambda e: load_tab(e.control.selected_index)
    )
    def load_tab(idx):
        nonlocal is_polling
        is_polling = (idx == 2)
        if is_polling: threading.Thread(target=poll_updates, daemon=True).start(); refresh_tabulation_tab()
        elif idx==0: refresh_config_tab()
        elif idx==1: refresh_c_tab()

    refresh_config_tab()

    return ft.Container(content=main_tabs, padding=10, expand=True)