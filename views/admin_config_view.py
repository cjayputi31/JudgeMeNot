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
    # Changed label to indicate % input
    p_seg_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    
    p_crit_name = ft.TextField(label="Criteria Name (e.g., Poise)", width=280)
    p_crit_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    
    selected_segment_id = None 

    def render_pageant_ui():
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        ui_column = ft.Column(spacing=20)
        
        ui_column.controls.append(ft.Row([
            ft.Text("Pageant Configuration", size=24, weight="bold"),
            ft.ElevatedButton("Add Segment", icon=ft.Icons.ADD, on_click=open_seg_dialog)
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
                            ft.Icon(ft.Icons.SUBDIRECTORY_ARROW_RIGHT, size=16),
                            ft.Text(f"{c.name}", weight="bold"),
                            ft.Text(f"Weight: {int(c.weight * 100)}%"),
                            ft.Text(f"Max: {c.max_score} pts"),
                        ]),
                        padding=ft.padding.only(left=20)
                    )
                )
            
            # FIX 1: Chip label must be a control (ft.Text), not a string
            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{seg.name}", size=18, weight="bold"),
                            ft.Chip(label=ft.Text(f"{int(seg.percentage_weight * 100)}% of Total")),
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE_OUTLINE, 
                                tooltip="Add Criteria",
                                data=seg.id,
                                on_click=open_crit_dialog
                            )
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
            # FIX 2: Treat input as whole number percentage (50 -> 0.50)
            raw_val = float(p_seg_weight.value)
            if raw_val > 1.0: 
                w = raw_val / 100.0
            else:
                w = raw_val # Allow 0.5 if they insist, but UI encourages 50
            
            success, msg = pageant_service.add_segment(event_id, p_seg_name.value, w, 1)
            if success:
                page.open(ft.SnackBar(ft.Text("Segment Added!"), bgcolor="green"))
                page.close(seg_dialog)
                p_seg_name.value = ""
                p_seg_weight.value = ""
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red"))

    def save_criteria(e):
        try:
            # FIX 2: Treat input as whole number percentage (50 -> 0.50)
            raw_val = float(p_crit_weight.value)
            if raw_val > 1.0:
                w = raw_val / 100.0
            else:
                w = raw_val
                
            success, msg = pageant_service.add_criteria(selected_segment_id, p_crit_name.value, w)
            if success:
                page.open(ft.SnackBar(ft.Text("Criteria Added!"), bgcolor="green"))
                page.close(crit_dialog)
                p_crit_name.value = ""
                p_crit_weight.value = ""
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red"))

    seg_dialog = ft.AlertDialog(
        title=ft.Text("Add Segment"),
        content=ft.Column([p_seg_name, p_seg_weight], height=150, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_segment)]
    )
    
    crit_dialog = ft.AlertDialog(
        title=ft.Text("Add Criteria"),
        content=ft.Column([p_crit_name, p_crit_weight], height=150, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_criteria)]
    )

    def open_seg_dialog(e):
        page.open(seg_dialog)

    def open_crit_dialog(e):
        nonlocal selected_segment_id
        selected_segment_id = e.control.data
        page.open(crit_dialog)

    # ---------------------------------------------------------
    # 3. QUIZ BEE SPECIFIC UI
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
            # FIX 1: Chip label must be a control (ft.Text)
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
                q_round_name.value = "" # Clear input
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