import flet as ft
from services.quiz_service import QuizService
from services.contestant_service import ContestantService
from services.admin_service import AdminService
from core.database import SessionLocal
from models.all_models import Segment, Contestant, User

def QuizConfigView(page: ft.Page, event_id: int):
    # Services
    quiz_service = QuizService()
    contestant_service = ContestantService()
    admin_service = AdminService() # To get Tabulators
    # State
    current_tab = "config" # config, contestants, tabulation

    # ---------------------------------------------------------
    # 1. CONFIGURATION TAB (Rounds)
    # ---------------------------------------------------------
    q_round_name = ft.TextField(label="Round Name (e.g. Easy)", width=300)
    q_points = ft.TextField(label="Points per Question", width=140, keyboard_type=ft.KeyboardType.NUMBER)
    q_total_qs = ft.TextField(label="Total Questions", width=140, keyboard_type=ft.KeyboardType.NUMBER)

    def save_round(e):
        try:
            pts = float(q_points.value)
            qs = int(q_total_qs.value)
            success, msg = quiz_service.add_round(event_id, q_round_name.value, pts, qs, 1)
            if success:
                page.open(ft.SnackBar(ft.Text("Round Added!"), bgcolor="green"))
                page.close(round_dialog)
                q_round_name.value = ""; q_points.value = ""; q_total_qs.value = ""
                refresh_config_tab()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Input (Numbers only for points/questions)"), bgcolor="red"))

    round_dialog = ft.AlertDialog(
        title=ft.Text("Add Quiz Round"),
        content=ft.Column([q_round_name, ft.Row([q_points, q_total_qs])], height=220, width=400, tight=True),
        actions=[ft.TextButton("Save", on_click=save_round)]
    )

    config_container = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def refresh_config_tab():
        config_container.controls.clear()

        # Header
        config_container.controls.append(
            ft.Row([
                ft.Text("Quiz Rounds", size=20, weight="bold"),
                ft.ElevatedButton("Add Round", icon=ft.Icons.ADD, on_click=lambda e: page.open(round_dialog))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )
        
        # Fetch Rounds
        db = SessionLocal()
        rounds = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        db.close()

        if not rounds:
            config_container.controls.append(ft.Text("No rounds configured yet.", italic=True, color="grey"))
        
        for r in rounds:
            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.QUIZ, color="blue"),
                            ft.Column([
                                ft.Text(f"{r.name}", size=18, weight="bold"),
                                ft.Text(f"{r.total_questions} Questions • {int(r.points_per_question)} pts each", size=12, color="grey"),
                            ])
                        ]),
                        # Future: Add Delete/Edit button here
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )

            config_container.controls.append(card)
        page.update()

    # ---------------------------------------------------------
    # 2. CONTESTANTS TAB (Unified List + Tabulator Assign)
    # ---------------------------------------------------------
    c_number = ft.TextField(label="School/Team #", width=100)
    c_name = ft.TextField(label="School/Participant Name", width=300)
    # We force "Mixed" or "Any" for Quiz Bee gender as it's often teams
    c_tabulator = ft.Dropdown(label="Assign Tabulator", width=300) 

    contestant_container = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def load_tabulators():
        users = admin_service.get_all_users()
        # Filter only Tabulators
        tabs = [u for u in users if u.role == "Tabulator"]
        c_tabulator.options = [ft.dropdown.Option(key=str(t.id), text=t.name) for t in tabs]

    def save_contestant(e):
        if not c_number.value or not c_name.value:
            page.open(ft.SnackBar(ft.Text("Please fill required fields"), bgcolor="red")); return
        
        # 1. Add Contestant
        success, msg = contestant_service.add_contestant(event_id, int(c_number.value), c_name.value, "Mixed")
        
        if success:
            # 2. Assign Tabulator if selected
            if c_tabulator.value:
                # We need a service method to link Tabulator -> Contestant
                # For now, let's assume we update the contestant record directly or use a helper
                # Since Contestant model has 'assigned_tabulator_id', we can update it.
                update_tabulator_assignment(int(c_number.value), int(c_tabulator.value))
            
            page.open(ft.SnackBar(ft.Text("Participant Added!"), bgcolor="green"))
            page.close(add_c_dialog)
            refresh_contestant_tab()
        else:
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    def update_tabulator_assignment(c_num, tab_id):
        # Quick helper to update the specific field
        db = SessionLocal()
        try:
            # Find the newly added contestant by Number + Event
            c = db.query(Contestant).filter(Contestant.event_id == event_id, Contestant.candidate_number == c_num).first()
            if c:
                c.assigned_tabulator_id = tab_id
                db.commit()
        except:
            pass
        finally:
            db.close()

    add_c_dialog = ft.AlertDialog(
        title=ft.Text("Add Participant"),
        content=ft.Column([c_number, c_name, c_tabulator], height=250, width=400, tight=True),
        actions=[ft.TextButton("Save", on_click=save_contestant)]
    )
    
    def refresh_contestant_tab():
        contestant_container.controls.clear()
        load_tabulators() # Refresh dropdown
        
        contestant_container.controls.append(
            ft.Row([
                ft.Text("Participants & Tabulators", size=20, weight="bold"),
                ft.ElevatedButton("Add Participant", icon=ft.Icons.ADD, on_click=lambda e: page.open(add_c_dialog))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        # Fetch Data
        db = SessionLocal()
        # Join User to get Tabulator Name
        participants = db.query(Contestant).outerjoin(User, Contestant.assigned_tabulator_id == User.id)\
                         .filter(Contestant.event_id == event_id).order_by(Contestant.candidate_number).all()
        
        # Build Table
        # Columns: #, Name, Assigned Tabulator, Action
        rows = []
        for p in participants:
            tab_name = "Unassigned"
            if p.assigned_tabulator_id:
                # We need to fetch the name manually or use the relationship if set up in models
                # Using quick query for safety if relationship isn't perfect
                t_user = db.query(User).get(p.assigned_tabulator_id)
                if t_user: tab_name = t_user.name

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(p.candidate_number), weight="bold")),
                    ft.DataCell(ft.Text(p.name)),
                    ft.DataCell(ft.Container(
                        content=ft.Text(tab_name, size=12, color="white"),
                        bgcolor="orange" if tab_name == "Unassigned" else "blue",
                        padding=5, border_radius=5
                    )),
                    ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", data=p.id, 
                        on_click=lambda e: delete_contestant(e.control.data)))
                ])
            )
        db.close()

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Participant / School")),
                ft.DataColumn(ft.Text("Assigned Tabulator")),
                ft.DataColumn(ft.Text("Action")),
            ],
            rows=rows,
            border=ft.border.all(1, "grey"),
            heading_row_color=ft.Colors.BLUE_50,
            width=float("inf")
        )
        
        contestant_container.controls.append(table)
        page.update()

    def delete_contestant(c_id):
        contestant_service.delete_contestant(c_id)
        refresh_contestant_tab()

    # ---------------------------------------------------------
    # 3. TABULATION TAB (Unified Standings)
    # ---------------------------------------------------------
    tabulation_container = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def refresh_tabulation_tab():
        tabulation_container.controls.clear()
        
        # Header
        tabulation_container.controls.append(
            ft.Row([
                ft.Text("Live Quiz Standings", size=20, weight="bold"),
                ft.IconButton(icon=ft.Icons.REFRESH, on_click=lambda e: refresh_tabulation_tab())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        # Get Scores
        results = quiz_service.get_live_scores(event_id)
        
        # Build Simple Ranking Table
        rows = []
        for i, res in enumerate(results):
            rank = i + 1
            color = "black"
            if rank == 1: color = "gold"
            elif rank == 2: color = "silver"
            elif rank == 3: color = "brown"

            rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(rank), weight="bold", size=16, color=color)),
                    ft.DataCell(ft.Text(res['name'], weight="bold" if rank <= 3 else "normal")),
                    ft.DataCell(ft.Text(str(res['total_score']), weight="bold", size=16, color="green")),
                ])
            )

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Rank", weight="bold")),
                ft.DataColumn(ft.Text("Participant", weight="bold")),
                ft.DataColumn(ft.Text("Total Score", weight="bold"), numeric=True),
            ],
            rows=rows,
            border=ft.border.all(1, "grey"),
            heading_row_color=ft.Colors.GREEN_50,
            width=float("inf")
        )

        if not rows:
            tabulation_container.controls.append(ft.Text("No scores recorded yet.", italic=True))
        else:
            tabulation_container.controls.append(table)
        
        page.update()

    # ---------------------------------------------------------
    # MAIN LAYOUT
    # ---------------------------------------------------------
    # Initialize tabs with empty content, will be filled by refresh functions
    main_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="Configuration", icon=ft.Icons.SETTINGS, content=config_container),
            ft.Tab(text="Participants", icon=ft.Icons.PEOPLE, content=contestant_container),
            ft.Tab(text="Tabulation", icon=ft.Icons.LEADERBOARD, content=tabulation_container),
        ],
        on_change=lambda e: load_current_tab(e.control.selected_index),
        expand=True
    )

    def load_current_tab(index):
        if index == 0: refresh_config_tab()
        elif index == 1: refresh_contestant_tab()
        elif index == 2: refresh_tabulation_tab()

    # Initial Load
    refresh_config_tab()

    return ft.Container(content=main_tabs, padding=10, expand=True)