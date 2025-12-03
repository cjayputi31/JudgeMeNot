import flet as ft
from services.pageant_service import PageantService
from services.quiz_service import QuizService
from core.database import SessionLocal
from models.all_models import Event, Segment, Criteria

def AdminConfigView(page: ft.Page, event_id: int):
    # Services
    pageant_service = PageantService()
    quiz_service = QuizService()

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
    # 2. PAGEANT SPECIFIC UI
    # ---------------------------------------------------------
    p_seg_name = ft.TextField(label="Segment Name (e.g., Swimwear)", width=280)
    p_seg_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    
    p_crit_name = ft.TextField(label="Criteria Name (e.g., Poise)", width=280)
    p_crit_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    
    # State tracking for edits
    selected_segment_id = None 
    editing_segment_id = None # If set, we are updating, not adding
    editing_criteria_id = None # If set, we are updating, not adding

    def render_pageant_ui():
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        ui_column = ft.Column(spacing=20)
        
        ui_column.controls.append(ft.Row([
            ft.Text("Pageant Configuration", size=24, weight="bold"),
            ft.ElevatedButton("Add Segment", icon=ft.Icons.ADD, on_click=open_add_seg_dialog)
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
                            # Edit Criteria Button
                            ft.IconButton(
                                icon=ft.Icons.EDIT, 
                                icon_size=16, 
                                tooltip="Edit Criteria",
                                data=c, # Pass entire object to pre-fill
                                on_click=open_edit_crit_dialog
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.only(left=20),
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=5
                    )
                )
            
            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Row([
                            ft.Row([
                                ft.Text(f"{seg.name}", size=18, weight="bold"),
                                ft.Chip(label=ft.Text(f"{int(seg.percentage_weight * 100)}% of Total")),
                            ]),
                            ft.Row([
                                # Edit Segment Button
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Edit Segment",
                                    data=seg, # Pass entire object
                                    on_click=open_edit_seg_dialog
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ADD_CIRCLE_OUTLINE, 
                                    tooltip="Add Criteria",
                                    data=seg.id,
                                    on_click=open_add_crit_dialog
                                )
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        crit_list if criterias else ft.Text("No criteria added yet.", italic=True, color="grey")
                    ])
                )
            )
            ui_column.controls.append(card)
        
        # Total Warning
        if current_total_weight > 1.0:
            ui_column.controls.append(ft.Text(f"⚠️ Total Weight is {int(current_total_weight*100)}%. It should be 100%.", color="red"))
        elif current_total_weight < 1.0:
            ui_column.controls.append(ft.Text(f"ℹ️ Total Weight is {int(current_total_weight*100)}%. Add more segments.", color="blue"))
        else:
             ui_column.controls.append(ft.Text("✅ Total Weight is 100%. Config Complete.", color="green"))

        db.close()
        return ui_column

    def save_segment(e):
        try:
            raw_val = float(p_seg_weight.value)
            # Smart Convert: If they type 50, treat as 0.5. If 0.5, treat as 0.5
            if raw_val > 1.0: 
                w = raw_val / 100.0
            else:
                w = raw_val 
            
            if editing_segment_id:
                # UPDATE EXISTING
                success, msg = pageant_service.update_segment(editing_segment_id, p_seg_name.value, w)
            else:
                # CREATE NEW
                success, msg = pageant_service.add_segment(event_id, p_seg_name.value, w, 1)

            if success:
                page.open(ft.SnackBar(ft.Text("Segment Saved!"), bgcolor="green"))
                page.close(seg_dialog)
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red"))

    def save_criteria(e):
        try:
            raw_val = float(p_crit_weight.value)
            if raw_val > 1.0:
                w = raw_val / 100.0
            else:
                w = raw_val
            
            if editing_criteria_id:
                # UPDATE EXISTING
                success, msg = pageant_service.update_criteria(editing_criteria_id, p_crit_name.value, w)
            else:
                # CREATE NEW
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
        content=ft.Column([p_seg_name, p_seg_weight], height=150, width=300, tight=True),
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
        editing_segment_id = None # Reset edit mode
        p_seg_name.value = ""
        p_seg_weight.value = ""
        seg_dialog.title.value = "Add Segment"
        page.open(seg_dialog)

    def open_edit_seg_dialog(e):
        nonlocal editing_segment_id
        seg_data = e.control.data
        editing_segment_id = seg_data.id # Set edit mode
        
        # Pre-fill fields
        p_seg_name.value = seg_data.name
        # Convert 0.5 back to 50 for easier editing
        p_seg_weight.value = str(int(seg_data.percentage_weight * 100))
        
        seg_dialog.title.value = "Edit Segment"
        page.open(seg_dialog)

    def open_add_crit_dialog(e):
        nonlocal selected_segment_id, editing_criteria_id
        selected_segment_id = e.control.data
        editing_criteria_id = None # Reset edit mode
        
        p_crit_name.value = ""
        p_crit_weight.value = ""
        crit_dialog.title.value = "Add Criteria"
        page.open(crit_dialog)

    def open_edit_crit_dialog(e):
        nonlocal editing_criteria_id
        crit_data = e.control.data
        editing_criteria_id = crit_data.id # Set edit mode
        
        # Pre-fill fields
        p_crit_name.value = crit_data.name
        p_crit_weight.value = str(int(crit_data.weight * 100))
        
        crit_dialog.title.value = "Edit Criteria"
        page.open(crit_dialog)

    # ---------------------------------------------------------
    # 3. QUIZ BEE SPECIFIC UI (Simplified for brevity - same logic applies)
    # ---------------------------------------------------------
    q_round_name = ft.TextField(label="Round Name (e.g., Easy)", width=280)
    q_points = ft.TextField(label="Points per Question", value="1", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    q_total_qs = ft.TextField(label="Total Questions", value="10", keyboard_type=ft.KeyboardType.NUMBER, width=280)

    def render_quiz_ui():
        db = SessionLocal()
        rounds = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        ui_column = ft.Column(spacing=20)
        
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
        return ui_column

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
    # 4. MAIN LAYOUT ASSEMBLY
    # ---------------------------------------------------------
    content_area = ft.Column(expand=True, scroll="adaptive")

    def refresh_ui():
        content_area.controls.clear()
        
        content_area.controls.append(
            ft.TextButton("Back to Dashboard", icon=ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/admin"))
        )
        
        content_area.controls.append(
            ft.Text(f"Configuring: {current_event.name}", size=30, weight="bold", color=ft.Colors.BLUE)
        )
        content_area.controls.append(ft.Divider())

        if current_event.event_type == "Pageant":
            content_area.controls.append(render_pageant_ui())
        else:
            content_area.controls.append(render_quiz_ui())
        
        page.update()

    refresh_ui()

    return ft.Container(
        content=content_area,
        padding=20,
        expand=True
    )