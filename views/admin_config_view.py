import flet as ft
from services.admin_service import AdminService
from services.pageant_service import PageantService
from services.quiz_service import QuizService
from core.database import SessionLocal
from models.all_models import Event, Segment, Criteria

def AdminConfigView(page: ft.Page, event_id: int):
    # Services
    admin_service = AdminService() # To fetch event details
    pageant_service = PageantService()
    quiz_service = QuizService()

    # State
    current_event = None
    
    # ---------------------------------------------------------
    # 1. DATA FETCHING
    # ---------------------------------------------------------
    def get_event_details():
        # Quick DB fetch to get the Event object
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
    # Controls for adding segments/criteria
    p_seg_name = ft.TextField(label="Segment Name (e.g., Swimwear)")
    p_seg_weight = ft.TextField(label="Weight (0.1 to 1.0)", keyboard_type=ft.KeyboardType.NUMBER)
    
    p_crit_name = ft.TextField(label="Criteria Name (e.g., Poise)")
    p_crit_weight = ft.TextField(label="Weight (0.1 to 1.0)", keyboard_type=ft.KeyboardType.NUMBER)
    
    selected_segment_id = None # Track which segment we are adding criteria to

    def render_pageant_ui():
        # Fetch fresh data
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        ui_column = ft.Column(spacing=20)
        
        # Header
        ui_column.controls.append(ft.Row([
            ft.Text("Pageant Configuration", size=24, weight="bold"),
            ft.ElevatedButton("Add Segment", icon=ft.Icons.ADD, on_click=open_seg_dialog)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        # List Segments
        for seg in segments:
            # Fetch Criteria for this segment
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
            
            # Segment Card
            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{seg.name}", size=18, weight="bold"),
                            ft.Chip(label=f"{int(seg.percentage_weight * 100)}% of Total"),
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE_OUTLINE, 
                                tooltip="Add Criteria",
                                data=seg.id, # Store ID to know where to add criteria
                                on_click=open_crit_dialog
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        crit_list if criterias else ft.Text("No criteria added yet.", italic=True, color="grey")
                    ])
                )
            )
            ui_column.controls.append(card)
        
        db.close()
        return ui_column

    # Pageant Actions
    def save_segment(e):
        try:
            w = float(p_seg_weight.value)
            success, msg = pageant_service.add_segment(event_id, p_seg_name.value, w, 1)
            if success:
                page.snack_bar = ft.SnackBar(ft.Text("Segment Added!"))
                page.dialog.open = False
                refresh_ui()
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red")
        except ValueError:
             page.snack_bar = ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red")
        page.snack_bar.open = True
        page.update()

    def save_criteria(e):
        try:
            w = float(p_crit_weight.value)
            # selected_segment_id is set when opening the dialog
            success, msg = pageant_service.add_criteria(selected_segment_id, p_crit_name.value, w)
            if success:
                page.snack_bar = ft.SnackBar(ft.Text("Criteria Added!"))
                page.dialog.open = False
                refresh_ui()
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red")
        except ValueError:
             page.snack_bar = ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red")
        page.snack_bar.open = True
        page.update()

    # Pageant Dialogs
    seg_dialog = ft.AlertDialog(
        title=ft.Text("Add Segment"),
        content=ft.Column([p_seg_name, p_seg_weight], height=150),
        actions=[ft.TextButton("Save", on_click=save_segment)]
    )
    
    crit_dialog = ft.AlertDialog(
        title=ft.Text("Add Criteria"),
        content=ft.Column([p_crit_name, p_crit_weight], height=150),
        actions=[ft.TextButton("Save", on_click=save_criteria)]
    )

    def open_seg_dialog(e):
        page.dialog = seg_dialog
        seg_dialog.open = True
        page.update()

    def open_crit_dialog(e):
        nonlocal selected_segment_id
        selected_segment_id = e.control.data # Get the segment ID from the button
        page.dialog = crit_dialog
        crit_dialog.open = True
        page.update()

    # ---------------------------------------------------------
    # 3. QUIZ BEE SPECIFIC UI
    # ---------------------------------------------------------
    q_round_name = ft.TextField(label="Round Name (e.g., Easy)")
    q_points = ft.TextField(label="Points per Question", value="1", keyboard_type=ft.KeyboardType.NUMBER)
    q_total_qs = ft.TextField(label="Total Questions", value="10", keyboard_type=ft.KeyboardType.NUMBER)

    def render_quiz_ui():
        db = SessionLocal()
        rounds = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        ui_column = ft.Column(spacing=20)
        
        # Header
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
                        ft.Chip(label=f"{int(r.points_per_question)} pts/question", bgcolor=ft.Colors.GREEN_100),
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
                page.snack_bar = ft.SnackBar(ft.Text("Round Added!"))
                page.dialog.open = False
                refresh_ui()
            else:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red")
        except ValueError:
             page.snack_bar = ft.SnackBar(ft.Text("Invalid Input"), bgcolor="red")
        page.snack_bar.open = True
        page.update()

    round_dialog = ft.AlertDialog(
        title=ft.Text("Add Round"),
        content=ft.Column([q_round_name, q_points, q_total_qs], height=200),
        actions=[ft.TextButton("Save", on_click=save_round)]
    )

    def open_round_dialog(e):
        page.dialog = round_dialog
        round_dialog.open = True
        page.update()

    # ---------------------------------------------------------
    # 4. MAIN LAYOUT ASSEMBLY
    # ---------------------------------------------------------
    content_area = ft.Column(expand=True, scroll="adaptive")

    def refresh_ui():
        content_area.controls.clear()
        
        # Back Button
        content_area.controls.append(
            ft.TextButton("Back to Dashboard", icon=ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/admin"))
        )
        
        # Event Title
        content_area.controls.append(
            ft.Text(f"Configuring: {current_event.name}", size=30, weight="bold", color=ft.Colors.BLUE)
        )
        content_area.controls.append(ft.Divider())

        # Render Logic
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