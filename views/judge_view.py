import flet as ft
from services.pageant_service import PageantService
from services.contestant_service import ContestantService

def JudgeView(page: ft.Page, on_logout_callback):
    # Services
    pageant_service = PageantService()
    contestant_service = ContestantService()
    
    # Session Data
    judge_id = page.session.get("user_id")
    judge_name = page.session.get("user_name")

    # App State
    current_event = None
    current_contestant = None
    
    # Layout Containers
    main_container = ft.Container(expand=True, padding=20)

    # ---------------------------------------------------------
    # 1. HEADER (Simple Mobile Friendly)
    # ---------------------------------------------------------
    header = ft.Row([
        ft.Column([
            ft.Text(f"Judge: {judge_name}", weight="bold", size=16),
            ft.Text("Scoring Panel", size=12, color="grey")
        ]),
        ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="red", on_click=on_logout_callback)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # ---------------------------------------------------------
    # 2. VIEW: SELECT EVENT
    # ---------------------------------------------------------
    def load_event_list():
        events = pageant_service.get_active_pageants()
        
        controls = [
            ft.Text("Select Active Event", size=24, weight="bold"),
            ft.Divider()
        ]

        if not events:
            controls.append(ft.Text("No active pageants found.", color="red"))
        
        grid = ft.GridView(expand=True, runs_count=2, max_extent=200, child_aspect_ratio=1.0, spacing=10)
        
        for e in events:
            grid.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.PINK_50,
                    border=ft.border.all(1, ft.Colors.PINK_200),
                    border_radius=10,
                    padding=20,
                    content=ft.Column([
                        ft.Icon(ft.Icons.STAR, size=40, color=ft.Colors.PINK),
                        ft.Text(e.name, weight="bold", size=16, text_align="center"),
                        ft.ElevatedButton("Enter", data=e, on_click=lambda x: select_event(x.control.data))
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    on_click=lambda x, e=e: select_event(e) # Click card to enter
                )
            )
        
        controls.append(grid)
        main_container.content = ft.Column(controls, expand=True)
        page.update()

    def select_event(event):
        nonlocal current_event
        current_event = event
        load_candidate_list()

    # ---------------------------------------------------------
    # 3. VIEW: SELECT CANDIDATE
    # ---------------------------------------------------------
    def load_candidate_list():
        candidates = contestant_service.get_contestants(current_event.id)
        
        controls = [
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: load_event_list()),
                ft.Text(current_event.name, size=20, weight="bold")
            ]),
            ft.Text("Select Candidate to Score", size=16),
            ft.Divider()
        ]

        list_view = ft.ListView(expand=True, spacing=10)
        
        for c in candidates:
            # Check if partially scored? (Advanced feature for later)
            list_view.controls.append(
                ft.ListTile(
                    leading=ft.CircleAvatar(content=ft.Text(str(c.candidate_number))),
                    title=ft.Text(c.name, weight="bold"),
                    subtitle=ft.Text(f"Candidate #{c.candidate_number}"),
                    trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                    bgcolor=ft.Colors.GREY_100,
                    on_click=lambda x, c=c: select_candidate(c)
                )
            )
        
        controls.append(list_view)
        main_container.content = ft.Column(controls, expand=True)
        page.update()

    def select_candidate(candidate):
        nonlocal current_contestant
        current_contestant = candidate
        load_scoring_form()

    # ---------------------------------------------------------
    # 4. VIEW: SCORING FORM (Dynamic)
    # ---------------------------------------------------------
    def load_scoring_form():
        # Fetch structure (Segments -> Criteria)
        structure = pageant_service.get_event_structure(current_event.id)
        # Fetch existing scores to pre-fill
        existing_scores = pageant_service.get_judge_scores(judge_id, current_contestant.id)
        
        # UI State for input values
        input_refs = {} # {criteria_id: TextField}

        form_controls = [
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: load_candidate_list()),
                ft.Column([
                    ft.Text(current_contestant.name, size=20, weight="bold"),
                    ft.Text(f"Candidate #{current_contestant.candidate_number}", size=12)
                ])
            ]),
            ft.Divider()
        ]

        # Build dynamic inputs
        scrollable_content = ft.Column(scroll="adaptive", expand=True, spacing=20)
        
        for item in structure:
            segment = item['segment']
            criterias = item['criteria']
            
            # Segment Header
            scrollable_content.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.BLUE_50, padding=10, border_radius=5,
                    content=ft.Text(f"{segment.name} ({int(segment.percentage_weight*100)}%)", weight="bold", color=ft.Colors.BLUE)
                )
            )
            
            # Criteria Inputs
            for crit in criterias:
                # Pre-fill value
                current_val = existing_scores.get(crit.id, "")
                
                # Input Field
                score_input = ft.TextField(
                    label=f"{crit.name} (Max: {crit.max_score})",
                    value=str(current_val) if current_val != "" else "",
                    keyboard_type=ft.KeyboardType.NUMBER,
                    width=150,
                    text_align=ft.TextAlign.RIGHT,
                    border_color=ft.Colors.BLUE_200
                )
                
                # Store ref to retrieve value later
                input_refs[crit.id] = {
                    "field": score_input,
                    "max": crit.max_score
                }
                
                scrollable_content.controls.append(
                    ft.Row([
                        ft.Text(crit.name, expand=True),
                        score_input
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            
            scrollable_content.controls.append(ft.Divider(height=5, color="transparent"))

        form_controls.append(scrollable_content)

        # Submit Action
        def submit_click(e):
            errors = []
            valid_scores = []

            # Validation Loop
            for crit_id, data in input_refs.items():
                field = data['field']
                max_val = data['max']
                val_str = field.value.strip()
                
                if not val_str:
                    field.error_text = "Required"
                    errors.append("Missing fields")
                    continue
                
                try:
                    val = float(val_str)
                    if val < 0 or val > max_val:
                        field.error_text = f"Max {max_val}"
                        errors.append(f"Score out of range")
                    else:
                        field.error_text = None
                        valid_scores.append((crit_id, val))
                except ValueError:
                    field.error_text = "Number only"
                    errors.append("Invalid number")
            
            page.update()
            
            if errors:
                page.open(ft.SnackBar(ft.Text("Please fix errors before submitting."), bgcolor="red"))
                return

            # Save to Database
            success_count = 0
            for crit_id, score_val in valid_scores:
                res, _ = pageant_service.submit_score(judge_id, current_contestant.id, crit_id, score_val)
                if res: success_count += 1
            
            page.open(ft.SnackBar(ft.Text(f"Saved {success_count} scores!"), bgcolor="green"))
            # Optional: Auto-go back? 
            # load_candidate_list() 

        submit_btn = ft.ElevatedButton(
            "Submit Scores", 
            icon=ft.Icons.CHECK, 
            bgcolor=ft.Colors.GREEN, 
            color="white",
            width=200,
            height=50,
            on_click=submit_click
        )
        
        form_controls.append(ft.Container(content=submit_btn, alignment=ft.alignment.center, padding=10))

        main_container.content = ft.Column(form_controls, expand=True)
        page.update()

    # Initial Load
    load_event_list()

    return ft.Column([
        ft.Container(content=header, padding=10, bgcolor=ft.Colors.GREY_100),
        main_container
    ], expand=True)