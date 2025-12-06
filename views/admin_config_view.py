import flet as ft
from services.pageant_service import PageantService
from services.quiz_service import QuizService
from services.contestant_service import ContestantService 
from core.database import SessionLocal
from models.all_models import Event, Segment, Criteria

def AdminConfigView(page: ft.Page, event_id: int):
    # Services
    pageant_service = PageantService()
    quiz_service = QuizService()
    contestant_service = ContestantService() 

    # State
    current_event = None
    
    # ---------------------------------------------------------
    # 1. DATA FETCHING
    # ---------------------------------------------------------
    def get_event_details():
        db = SessionLocal()
        event = db.query(Event).get(event_id)
        db.close()
        return event

    current_event = get_event_details()
    if not current_event:
        return ft.Container(content=ft.Text("Event not found!"))

    # ---------------------------------------------------------
    # 2. CONTESTANT MANAGEMENT UI (TAB 2)
    # ---------------------------------------------------------
    c_number = ft.TextField(label="#", width=80, keyboard_type=ft.KeyboardType.NUMBER)
    c_name = ft.TextField(label="Name (e.g., Mary or Team Red)", expand=True)
    c_gender = ft.Dropdown(
        label="Gender", width=120,
        options=[ft.dropdown.Option("Female"), ft.dropdown.Option("Male"), ft.dropdown.Option("N/A")],
        value="N/A"
    )

    def render_contestant_tab():
        contestants = contestant_service.get_contestants(event_id)
        
        add_row = ft.Row([
            c_number, 
            c_name, 
            c_gender,
            ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_size=40, icon_color="blue", on_click=add_contestant_click)
        ])

        list_column = ft.Column(spacing=10, scroll="adaptive")
        
        for c in contestants:
            bg_col = ft.Colors.PINK_50 if c.gender == "Female" else (ft.Colors.BLUE_50 if c.gender == "Male" else ft.Colors.GREY_100)
            icon = ft.Icons.WOMAN if c.gender == "Female" else (ft.Icons.MAN if c.gender == "Male" else ft.Icons.GROUPS)
            
            list_column.controls.append(
                ft.Container(
                    padding=10,
                    bgcolor=bg_col,
                    border_radius=10,
                    content=ft.Row([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"#{c.candidate_number}", size=20, weight="bold", color="white"),
                                bgcolor="black", padding=10, border_radius=5
                            ),
                            ft.Icon(icon),
                            ft.Text(c.name, size=18)
                        ]),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, 
                            icon_color="red", 
                            data=c.id, 
                            on_click=delete_contestant_click
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )

        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Manage Participants", size=20, weight="bold"),
                ft.Text("Add candidates or teams below.", size=14, color="grey"),
                ft.Divider(),
                add_row,
                ft.Divider(),
                list_column
            ])
        )

    def add_contestant_click(e):
        if not c_number.value or not c_name.value:
            page.open(ft.SnackBar(ft.Text("Fill Number and Name"), bgcolor="red"))
            return
            
        try:
            num = int(c_number.value)
            success, msg = contestant_service.add_contestant(event_id, num, c_name.value, c_gender.value)
            if success:
                page.open(ft.SnackBar(ft.Text("Contestant Added!"), bgcolor="green"))
                c_name.value = ""
                c_number.value = str(num + 1) 
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Number must be an integer"), bgcolor="red"))

    def delete_contestant_click(e):
        c_id = e.control.data
        success, msg = contestant_service.delete_contestant(c_id)
        if success:
            page.open(ft.SnackBar(ft.Text("Deleted"), bgcolor="grey"))
            refresh_ui()
        else:
             page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    # ---------------------------------------------------------
    # 3. PAGEANT CONFIGURATION UI (TAB 1)
    # ---------------------------------------------------------
    p_seg_name = ft.TextField(label="Segment Name", width=280)
    p_seg_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    
    p_crit_name = ft.TextField(label="Criteria Name", width=280)
    p_crit_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)

    p_is_final = ft.Checkbox(label="Is Final Round?", value=False)
    p_qualifiers = ft.TextField(label="Qualifiers Count", value="5", width=280, visible=False, keyboard_type=ft.KeyboardType.NUMBER)

    
    selected_segment_id = None 
    editing_segment_id = None 
    editing_criteria_id = None 
    
    # --- SAFETY CONFIRMATION STATE ---
    pending_action_seg_id = None # Stores the ID we want to activate/deactivate
    
    def on_final_check(e):
        # Toggle visibility of qualifiers input and weight
        p_qualifiers.visible = p_is_final.value
        # If final, weight implies 100% of the reset score, but usually we just leave it for criteria weight
        p_seg_weight.disabled = p_is_final.value 
        if p_is_final.value: p_seg_weight.value = "100" # Visual only
        page.update()

    p_is_final.on_change = on_final_check

    # 1. Simple Confirm Dialog
    def confirm_simple_action(e):
        execute_toggle(pending_action_seg_id)
        page.close(simple_dialog)

    simple_dialog = ft.AlertDialog(
        title=ft.Text("Confirm Activation"),
        content=ft.Text("Are you sure you want to activate this segment?"),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(simple_dialog)),
            ft.TextButton("Yes, Activate", on_click=confirm_simple_action),
        ]
    )

    # 2. Strict Confirm Dialog (Requires Typing)
    confirm_input = ft.TextField(label="Type CONFIRM", border_color="red")
    confirm_btn = ft.ElevatedButton("Proceed", bgcolor="red", color="white", disabled=True)

    def validate_strict_input(e):
        confirm_btn.disabled = (confirm_input.value != "CONFIRM")
        confirm_btn.update()

    def confirm_strict_action(e):
        execute_toggle(pending_action_seg_id)
        page.close(strict_dialog)
        confirm_input.value = "" # Reset

    confirm_btn.on_click = confirm_strict_action
    confirm_input.on_change = validate_strict_input

    strict_dialog = ft.AlertDialog(
        title=ft.Row([ft.Icon(ft.Icons.WARNING, color="red"), ft.Text("Warning: Disruptive Action")]),
        content=ft.Column([
            ft.Text("You are about to deactivate the current segment or swap to a new one."),
            ft.Text("Judges might be in the middle of scoring!"),
            ft.Container(height=10),
            ft.Text("Type 'CONFIRM' to proceed:", size=12, weight="bold"),
            confirm_input
        ], tight=True, width=400),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(strict_dialog)),
            confirm_btn
        ]
    )

    # Main Logic to decide which dialog to show
    def request_toggle_status(seg_id):
        nonlocal pending_action_seg_id
        pending_action_seg_id = seg_id
        
        # Check if there is currently an active segment
        active_seg = pageant_service.get_active_segment(event_id)
        
        # Scenario A: Deactivate All (seg_id is None) -> STRICT
        if seg_id is None:
            if not active_seg: return # Nothing to do
            page.open(strict_dialog)
            return

        # Scenario B: Swapping (Active exists, and it's different) -> STRICT
        if active_seg and active_seg.id != seg_id:
            page.open(strict_dialog)
            return
            
        # Scenario C: Deactivating Self -> STRICT
        if active_seg and active_seg.id == seg_id:
             page.open(strict_dialog)
             return

        # Scenario D: Just Activating (No current active) -> SIMPLE
        page.open(simple_dialog)

    def execute_toggle(seg_id):
        success, msg = pageant_service.set_active_segment(event_id, seg_id)
        if success:
            page.open(ft.SnackBar(ft.Text(msg), bgcolor="green"))
            refresh_ui()
        else:
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    # --- UI RENDERER ---
    def render_pageant_ui():
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        ui_column = ft.Column(spacing=20, scroll="adaptive")
        
        # Header Row
        ui_column.controls.append(ft.Row([
            ft.Text("Pageant Configuration", size=24, weight="bold"),
            ft.Row([
                ft.OutlinedButton("Deactivate All", icon=ft.Icons.STOP_CIRCLE, 
                                  style=ft.ButtonStyle(color="red"),
                                  on_click=lambda e: request_toggle_status(None)), # Calls Check
                ft.ElevatedButton("Add Segment", icon=ft.Icons.ADD, on_click=open_add_seg_dialog)
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        current_total_weight = 0.0

        for seg in segments:
            current_total_weight += seg.percentage_weight
            criterias = db.query(Criteria).filter(Criteria.segment_id == seg.id).all()
            
            crit_list = ft.Column(spacing=5)
            for c in criterias:
                crit_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.SUBDIRECTORY_ARROW_RIGHT, size=16, color="grey"),
                                ft.Text(f"{c.name}", weight="bold"),
                                ft.Text(f"Weight: {int(c.weight * 100)}%"),
                                ft.Text(f"Max: {c.max_score} pts"),
                            ]),
                            ft.IconButton(icon=ft.Icons.EDIT, icon_size=16, tooltip="Edit Criteria", data=c, on_click=open_edit_crit_dialog)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.only(left=20),
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=5
                    )
                )

            # STATUS INDICATOR
            if seg.is_active:
                status_color = ft.Colors.GREEN_50
                status_text = "ACTIVE"
                status_icon = ft.Icons.RADIO_BUTTON_CHECKED
                action_tooltip = "Deactivate"
                border_side = ft.border.all(2, ft.Colors.GREEN)
            else:
                status_color = ft.Colors.WHITE
                status_text = "INACTIVE"
                status_icon = ft.Icons.RADIO_BUTTON_UNCHECKED
                action_tooltip = "Set Active"
                border_side = None

            # NEW: DIFFERENT CARD COLOR FOR FINAL ROUND
            if seg.is_final:
                card_bg = ft.Colors.AMBER_50
                badge = ft.Container(content=ft.Text(f"FINAL ROUND (Top {seg.qualifier_limit})", color="black", weight="bold"), bgcolor=ft.Colors.AMBER_300, padding=5, border_radius=5)
            else:
                card_bg = ft.Colors.WHITE
                badge = ft.Chip(label=ft.Text(f"{int(seg.percentage_weight * 100)}%"))

            card = ft.Card(
                content=ft.Container(
                    bgcolor=status_color,
                    border=border_side,
                    padding=15,
                    content=ft.Column([
                        ft.Row([
                            ft.Row([
                                # Activation Button (Calls request_toggle_status)
                                ft.IconButton(
                                    icon=status_icon, 
                                    icon_color="green" if seg.is_active else "grey",
                                    tooltip=action_tooltip,
                                    data=seg.id,
                                    on_click=lambda e: request_toggle_status(e.control.data)
                                ),
                                ft.Text(f"{seg.name}", size=18, weight="bold"),
                                ft.Chip(label=ft.Text(f"{int(seg.percentage_weight * 100)}%")),
                                ft.Container(
                                    content=ft.Text(status_text, size=10, color="white", weight="bold"),
                                    bgcolor="green" if seg.is_active else "grey",
                                    padding=5, border_radius=5
                                )
                            ]),
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.EDIT, tooltip="Edit", data=seg, on_click=open_edit_seg_dialog),
                                ft.IconButton(icon=ft.Icons.ADD_CIRCLE_OUTLINE, tooltip="Add Criteria", data=seg.id, on_click=open_add_crit_dialog)
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        crit_list if criterias else ft.Text("No criteria added yet.", italic=True, color="grey")
                    ])
                )
            )
            ui_column.controls.append(card)
        
        if current_total_weight > 1.0:
            ui_column.controls.append(ft.Text(f"⚠️ Total Weight is {int(current_total_weight*100)}%. It should be 100%.", color="red"))
        elif current_total_weight < 1.0:
            ui_column.controls.append(ft.Text(f"ℹ️ Total Weight is {int(current_total_weight*100)}%. Add more segments.", color="blue"))
        else:
             ui_column.controls.append(ft.Text("✅ Total Weight is 100%. Config Complete.", color="green"))

        db.close()
        return ft.Container(content=ui_column, padding=20)

    def request_final_activation(seg_id):
        # 1. Get Rankings Preview
        # We need to temporarily fetch the segment object to get the limit
        db = SessionLocal()
        seg = db.query(Segment).get(seg_id)
        limit = seg.qualifier_limit
        db.close()

        # 2. Calculate who qualifies
        rankings = pageant_service.get_preliminary_rankings(event_id)
        
        qualifiers_list = []
        eliminated_list = []
        
        for i, r in enumerate(rankings):
            line = f"#{i+1} {r['contestant'].name} - {r['score']}%"
            if i < limit:
                qualifiers_list.append(ft.Text(line, weight="bold", color="green"))
            else:
                eliminated_list.append(ft.Text(line, color="grey"))

        # 3. Show Confirmation Dialog
        final_confirm_dialog = ft.AlertDialog(
            title=ft.Text("Confirm Final Round"),
            content=ft.Column([
                ft.Text(f"Activating this will ELIMINATE candidates below Rank {limit}.", color="red"),
                ft.Divider(),
                ft.Text("QUALIFIERS (Scores Reset to 0):", weight="bold"),
                ft.Column(qualifiers_list),
                ft.Divider(),
                ft.Text("ELIMINATED:", weight="bold"),
                ft.Column(eliminated_list),
            ], scroll="adaptive", height=300, width=400),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(final_confirm_dialog)),
                ft.ElevatedButton("CONFIRM & ACTIVATE", bgcolor="red", color="white", on_click=lambda e: execute_final_activation(seg_id, limit, final_confirm_dialog))
            ]
        )
        page.open(final_confirm_dialog)

    def execute_final_activation(seg_id, limit, dlg):
        success, q, e = pageant_service.activate_final_round(event_id, seg_id, limit)
        page.close(dlg)
        if success:
            page.open(ft.SnackBar(ft.Text(f"Final Round Active! {len(q)} Qualified."), bgcolor="green"))
            refresh_ui()
        else:
            page.open(ft.SnackBar(ft.Text("Error activating round."), bgcolor="red"))


    def save_segment(e):
        try:
            if not p_is_final.value:
                raw_val = float(p_seg_weight.value)
                w = raw_val / 100.0 if raw_val > 1.0 else raw_val
            else:
                w = 0 # Weight irrelevant for final round relative to prelims
            
            limit = int(p_qualifiers.value) if p_is_final.value else 0

            if editing_segment_id:
                success, msg = pageant_service.update_segment(editing_segment_id, p_seg_name.value, w, p_is_final.value, limit)
            else:
                success, msg = pageant_service.add_segment(event_id, p_seg_name.value, w, 1, p_is_final.value, limit)

            if success:
                page.open(ft.SnackBar(ft.Text("Saved!"), bgcolor="green"))
                page.close(seg_dialog)
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Input"), bgcolor="red"))


    def save_criteria(e):
        try:
            raw_val = float(p_crit_weight.value)
            if raw_val > 1.0:
                w = raw_val / 100.0
            else:
                w = raw_val
            
            if editing_criteria_id:
                success, msg = pageant_service.update_criteria(editing_criteria_id, p_crit_name.value, w)
            else:
                success, msg = pageant_service.add_criteria(selected_segment_id, p_crit_name.value, w)

            if success:
                page.open(ft.SnackBar(ft.Text("Criteria Saved!"), bgcolor="green"))
                page.close(crit_dialog)
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red"))

    # Dialogs
    seg_dialog = ft.AlertDialog(
        title=ft.Text("Segment Details"),
        content=ft.Column([p_seg_name, p_is_final, p_qualifiers, p_seg_weight], height=300, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_segment)]
    )
    
    crit_dialog = ft.AlertDialog(
        title=ft.Text("Criteria Details"),
        content=ft.Column([p_crit_name, p_crit_weight], height=150, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_criteria)]
    )

    # --- DIALOG OPENERS ---
    def open_add_seg_dialog(e):
        nonlocal editing_segment_id
        editing_segment_id = None 
        p_seg_name.value = ""
        p_seg_weight.value = ""
        seg_dialog.title.value = "Add Segment"
        page.open(seg_dialog)

    def open_edit_seg_dialog(e):
        nonlocal editing_segment_id
        seg_data = e.control.data
        editing_segment_id = seg_data.id 
        p_seg_name.value = seg_data.name
        p_seg_weight.value = str(int(seg_data.percentage_weight * 100))
        seg_dialog.title.value = "Edit Segment"
        page.open(seg_dialog)

    def open_add_crit_dialog(e):
        nonlocal selected_segment_id, editing_criteria_id
        selected_segment_id = e.control.data
        editing_criteria_id = None 
        p_crit_name.value = ""
        p_crit_weight.value = ""
        crit_dialog.title.value = "Add Criteria"
        page.open(crit_dialog)

    def open_edit_crit_dialog(e):
        nonlocal editing_criteria_id
        crit_data = e.control.data
        editing_criteria_id = crit_data.id 
        p_crit_name.value = crit_data.name
        p_crit_weight.value = str(int(crit_data.weight * 100))
        crit_dialog.title.value = "Edit Criteria"
        page.open(crit_dialog)

    # ---------------------------------------------------------
    # 4. QUIZ BEE CONFIGURATION UI (TAB 1 - Logic B)
    # ---------------------------------------------------------
    q_round_name = ft.TextField(label="Round Name (e.g., Easy)", width=280)
    q_points = ft.TextField(label="Points per Question", value="1", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    q_total_qs = ft.TextField(label="Total Questions", value="10", keyboard_type=ft.KeyboardType.NUMBER, width=280)

    def render_quiz_ui():
        db = SessionLocal()
        rounds = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        ui_column = ft.Column(spacing=20, scroll="adaptive")
        
        ui_column.controls.append(ft.Row([
            ft.Text("Quiz Bee Configuration", size=24, weight="bold"),
            ft.ElevatedButton("Add Round", icon=ft.Icons.ADD, on_click=open_round_dialog)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        for r in rounds:
            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"{r.name}", size=18, weight="bold"),
                            ft.Text(f"{r.total_questions} Questions"),
                        ]),
                        ft.Chip(label=ft.Text(f"{int(r.points_per_question)} pts/question"), bgcolor=ft.Colors.GREEN_100),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            ui_column.controls.append(card)
        
        db.close()
        return ft.Container(content=ui_column, padding=20)

    def save_round(e):
        try:
            pts = float(q_points.value)
            qs = int(q_total_qs.value)
            success, msg = quiz_service.add_round(event_id, q_round_name.value, pts, qs, 1)
            if success:
                page.open(ft.SnackBar(ft.Text("Round Added!"), bgcolor="green"))
                page.close(round_dialog)
                q_round_name.value = "" 
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Input"), bgcolor="red"))

    round_dialog = ft.AlertDialog(
        title=ft.Text("Add Round"),
        content=ft.Column([q_round_name, q_points, q_total_qs], height=220, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_round)]
    )

    def open_round_dialog(e):
        page.open(round_dialog)

    # ---------------------------------------------------------
    # 5. MAIN LAYOUT ASSEMBLY
    # ---------------------------------------------------------
    
    def render_config_tab():
        if current_event.event_type == "Pageant":
            return render_pageant_ui()
        else:
            return render_quiz_ui()

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="Configuration",
                icon=ft.Icons.SETTINGS,
                content=render_config_tab() 
            ),
            ft.Tab(
                text="Contestants",
                icon=ft.Icons.PEOPLE,
                content=render_contestant_tab() 
            ),
        ],
        expand=True
    )

    def refresh_ui():
        # Because we can't easily re-assign tab content in Flet 0.28+ without
        # potential issues, it is often safer to clear and rebuild the view controls
        # or update the specific tab content. 
        # Here we re-assign the content property which works for refresh.
        tabs.tabs[0].content = render_config_tab() 
        tabs.tabs[1].content = render_contestant_tab()
        page.update()

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/admin")),
                ft.Text(f"Event: {current_event.name}", size=24, weight="bold")
            ]),
            ft.Divider(),
            tabs
        ], expand=True),
        padding=20,
        expand=True
    )