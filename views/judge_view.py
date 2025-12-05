import flet as ft
from services.pageant_service import PageantService
from services.contestant_service import ContestantService
import time, threading

def JudgeView(page: ft.Page, on_logout_callback):
    # Services
    pageant_service = PageantService()
    contestant_service = ContestantService()
    
    # Session Data
    judge_id = page.session.get("user_id")
    judge_name = page.session.get("user_name")

    # App State
    current_event = None
    selected_segment = None
    
    # Polling State
    is_polling = False
    
    # Registry
    cards_registry = {}

    # Layout Containers
    main_container = ft.Container(expand=True, padding=10)

    # ---------------------------------------------------------
    # 0. POLLING LOGIC (RESTORED)
    # ---------------------------------------------------------
    def start_polling():
        nonlocal is_polling
        if is_polling: return 
        is_polling = True
        threading.Thread(target=poll_active_segment, daemon=True).start()

    def stop_polling():
        nonlocal is_polling
        is_polling = False

    def poll_active_segment():
        while is_polling and current_event:
            try:
                # 1. Check DB
                active_seg_db = pageant_service.get_active_segment(current_event.id)
                db_id = active_seg_db.id if active_seg_db else None
                
                # 2. Check Screen
                current_id = selected_segment['segment'].id if selected_segment else None
                
                # 3. Compare
                if db_id != current_id:
                    # If DB is None (Deactivated) != Screen (Active), this triggers.
                    # If DB is New ID != Screen Old ID, this triggers.
                    print(f"🔄 Auto-Refresh: {current_id} -> {db_id}")
                    enter_scoring_dashboard(current_event)
                
            except Exception as e:
                print(f"Polling Error: {e}")
            
            time.sleep(3)

    # ---------------------------------------------------------
    # 1. HEADER & GLOBAL SUBMIT LOGIC
    # ---------------------------------------------------------
    def submit_final_scores(e):
        missing_candidates = []
        
        for c_id, card_data in cards_registry.items():
            btn = card_data['btn']
            inputs = card_data['inputs']
            candidate_info = card_data['info'] 
            
            card_is_complete = True
            
            btn.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color="white")
            btn.update()

            for crit_id, ref in inputs.items():
                val_str = ref['field'].value
                max_val = ref['max']
                
                if not val_str:
                    ref['field'].border_color = "red"
                    card_is_complete = False
                    continue
                
                try:
                    val = float(val_str)
                    if val < 0 or val > max_val:
                        ref['field'].border_color = "red"
                        card_is_complete = False
                    else:
                        ref['field'].border_color = ft.Colors.GREEN
                        pageant_service.submit_score(judge_id, c_id, crit_id, val)
                except ValueError:
                    ref['field'].border_color = "red"
                    card_is_complete = False

            if card_is_complete:
                btn.bgcolor = ft.Colors.GREEN
                btn.content = ft.Row([ft.Icon(ft.Icons.CHECK, color="white", size=16), ft.Text("Saved", color="white")], alignment=ft.MainAxisAlignment.CENTER)
            else:
                btn.bgcolor = ft.Colors.ORANGE
                btn.content = ft.Text("Incomplete", color="white")
                missing_candidates.append(f"{candidate_info['name']} ({candidate_info['gender']})")
            
            btn.update()

        if missing_candidates:
            content = ft.Column(tight=True, spacing=10)
            content.controls.append(ft.Text("The following candidates have missing scores:", color="red"))
            for m in missing_candidates:
                content.controls.append(ft.Text(f"• {m}", weight="bold"))
            content.controls.append(ft.Container(height=10))
            content.controls.append(ft.Text("Look for the Orange buttons.", size=12, italic=True))

            dlg = ft.AlertDialog(
                title=ft.Text("Submission Incomplete"),
                content=content,
                actions=[ft.TextButton("OK", on_click=lambda e: page.close(dlg))]
            )
            page.open(dlg)
        else:
            page.open(ft.SnackBar(ft.Text("All scores submitted successfully!"), bgcolor="green"))

    submit_all_btn = ft.ElevatedButton(
        "Submit Final Tally", 
        icon=ft.Icons.PUBLISH,
        bgcolor=ft.Colors.GREEN_600,
        color="white",
        on_click=submit_final_scores
    )

    header = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.GAVEL, color=ft.Colors.WHITE),
                ft.Column([
                    ft.Text(f"Judge: {judge_name}", weight="bold", size=16, color="white"),
                    ft.Text("Scoring Panel", size=12, color=ft.Colors.WHITE70)
                ], spacing=2)
            ]),
            ft.Row([
                submit_all_btn,
                ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="white", on_click=on_logout_callback)
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=15,
        bgcolor=ft.Colors.BLUE_800,
        border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10)
    )

    # ---------------------------------------------------------
    # 2. SELECT EVENT
    # ---------------------------------------------------------
    def load_event_selector():
        stop_polling() # Stop background task when leaving dashboard
        
        events = pageant_service.get_active_pageants()
        
        grid = ft.GridView(expand=True, max_extent=300, spacing=20, run_spacing=20)
        
        for e in events:
            grid.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border=ft.border.all(1, ft.Colors.BLUE_100),
                    border_radius=15,
                    padding=20,
                    shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLUE_GREY_100),
                    content=ft.Column([
                        ft.Icon(ft.Icons.STAR_ROUNDED, size=50, color=ft.Colors.ORANGE),
                        ft.Text(e.name, weight="bold", size=18, text_align="center"),
                        ft.Text(f"Status: {e.status}", color="green"),
                        ft.ElevatedButton("Start Judging", width=150, on_click=lambda x, ev=e: enter_scoring_dashboard(ev))
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    on_click=lambda x, ev=e: enter_scoring_dashboard(ev)
                )
            )
        
        main_container.content = ft.Column([
            ft.Text("Select Active Event", size=24, weight="bold"),
            ft.Divider(),
            grid
        ], expand=True)
        page.update()

    # ---------------------------------------------------------
    # 3. SCORING DASHBOARD
    # ---------------------------------------------------------
    def enter_scoring_dashboard(event):
        nonlocal current_event, selected_segment
        current_event = event
        
        # 1. Fetch ACTIVE
        active_seg = pageant_service.get_active_segment(current_event.id)
        
        if not active_seg:
            selected_segment = None
            show_waiting_room()
            start_polling() # Keep polling until admin activates something
            return

        # 2. Load Data
        structure = pageant_service.get_event_structure(current_event.id)
        target_struct = next((s for s in structure if s['segment'].id == active_seg.id), None)
        
        if target_struct:
            selected_segment = target_struct
            render_dashboard(target_struct)
            start_polling() # Keep polling for changes/deactivation
        else:
            page.open(ft.SnackBar(ft.Text("Error loading data"), bgcolor="red"))

    def show_waiting_room():
        main_container.content = ft.Column([
            ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: load_event_selector())]),
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=50, height=50, stroke_width=4),
                    ft.Container(height=20),
                    ft.Text("Waiting for Admin...", size=24, weight="bold"),
                    ft.Text("No segment is currently active.", color="grey", size=16),
                    ft.Text("The screen will refresh automatically.", italic=True, color="blue"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                expand=True
            )
        ], expand=True)
        page.update()

    def render_dashboard(structure_item):
        segment_title = ft.Text(
            f"Segment: {structure_item['segment'].name}", 
            size=20, weight="bold", color=ft.Colors.BLUE_800
        )

        gender_selector = ft.SegmentedButton(
            selected={ "0" }, 
            segments=[
                ft.Segment(value="0", label=ft.Text("All"), icon=ft.Icon(ft.Icons.GROUPS)),
                ft.Segment(value="1", label=ft.Text("Female"), icon=ft.Icon(ft.Icons.WOMAN)),
                ft.Segment(value="2", label=ft.Text("Male"), icon=ft.Icon(ft.Icons.MAN)),
            ],
            on_change=lambda e: rebuild_view(int(list(e.control.selected)[0]))
        )

        content_area = ft.Container(expand=True)

        def rebuild_view(tab_index):
            cards_registry.clear()
            candidates = contestant_service.get_contestants(current_event.id)
            
            def get_cards(filter_gender, is_flow_layout=False):
                subset = [c for c in candidates if c.gender == filter_gender]
                res = []
                for c in subset:
                    scores = pageant_service.get_judge_scores(judge_id, c.id)
                    res.append(create_scoring_card(c, scores, set_fixed_width=is_flow_layout))
                return res

            if tab_index == 0: 
                header_male = ft.Container(content=ft.Text("Male Candidates", weight="bold", color=ft.Colors.BLUE), bgcolor=ft.Colors.BLUE_50, padding=10, border_radius=5, alignment=ft.alignment.center, width=float("inf"))
                male_cards = get_cards("Male", False)
                list_male = ft.Column(controls=male_cards, expand=True, scroll="hidden", spacing=15, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
                
                header_female = ft.Container(content=ft.Text("Female Candidates", weight="bold", color=ft.Colors.PINK), bgcolor=ft.Colors.PINK_50, padding=10, border_radius=5, alignment=ft.alignment.center, width=float("inf"))
                female_cards = get_cards("Female", False)
                list_female = ft.Column(controls=female_cards, expand=True, scroll="hidden", spacing=15, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

                content_area.content = ft.Row([
                    ft.Column([header_male, list_male], expand=True), 
                    ft.VerticalDivider(width=1),
                    ft.Column([header_female, list_female], expand=True)
                ], expand=True)

            else: 
                target = "Female" if tab_index == 1 else "Male"
                cards = get_cards(target, True)
                
                if not cards:
                    content_area.content = ft.Column(
                        [
                            ft.Icon(ft.Icons.SEARCH_OFF, size=50, color="grey"),
                            ft.Text("No candidates found.", italic=True, size=16, color="grey")
                        ], 
                        alignment=ft.MainAxisAlignment.CENTER, 
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True
                    )
                else:
                    content_area.content = ft.Column(
                        controls=[
                            ft.Row(
                                controls=cards, 
                                wrap=True, 
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=20,
                                run_spacing=20
                            )
                        ],
                        scroll="adaptive",
                        expand=True
                    )
            
            page.update()

        # 4. CARD CREATOR
        def create_scoring_card(contestant, existing_scores, set_fixed_width=False):
            border_color = ft.Colors.BLUE_200 if contestant.gender == "Male" else ft.Colors.PINK_200
            
            inputs_column = ft.Column(spacing=5)
            local_inputs = {} 
            current_criteria = structure_item['criteria']

            def on_input_change(e):
                btn = cards_registry[contestant.id]['btn']
                if btn.bgcolor != ft.Colors.BLUE:
                    btn.bgcolor = ft.Colors.BLUE
                    btn.content = ft.Text("Save Score", color="white")
                    btn.update()

            for crit in current_criteria:
                val = existing_scores.get(crit.id, "")
                
                tf = ft.TextField(
                    value=str(val) if val != "" else "",
                    width=80, 
                    height=35,
                    text_size=14,
                    content_padding=5,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    text_align=ft.TextAlign.CENTER,
                    border_color=ft.Colors.GREY_400,
                    bgcolor=ft.Colors.WHITE,
                    hint_text="0",
                    on_change=on_input_change
                )
                local_inputs[crit.id] = {"field": tf, "max": crit.max_score}
                
                inputs_column.controls.append(
                    ft.Container(
                        bgcolor=ft.Colors.GREY_50, padding=5, border_radius=5,
                        content=ft.Row([
                            ft.Text(crit.name, size=13, weight="w500", expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"/{int(crit.max_score)}", size=10, color="grey"), 
                            tf
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )

            def save_card(e):
                btn = e.control
                btn.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color="white")
                btn.disabled = True
                page.update()

                valid = True
                for crit_id, ref in local_inputs.items():
                    val_str = ref['field'].value
                    max_val = ref['max']
                    
                    if not val_str: 
                        valid = False 
                        ref['field'].border_color = "red"
                        continue 
                    
                    try:
                        val = float(val_str)
                        if val < 0 or val > max_val:
                            ref['field'].border_color = "red"
                            valid = False
                        else:
                            ref['field'].border_color = ft.Colors.GREEN
                            pageant_service.submit_score(judge_id, contestant.id, crit_id, val)
                    except ValueError:
                        ref['field'].border_color = "red"
                        valid = False
                
                if valid:
                    btn.bgcolor = ft.Colors.GREEN
                    btn.content = ft.Row([ft.Icon(ft.Icons.CHECK, color="white", size=16), ft.Text("Saved", color="white")], alignment=ft.MainAxisAlignment.CENTER)
                else:
                    btn.bgcolor = ft.Colors.ORANGE
                    btn.content = ft.Text("Incomplete", color="white")
                    btn.disabled = False 
                
                page.update()
                
                def revert():
                    time.sleep(4)
                    if btn.bgcolor != ft.Colors.BLUE: 
                        btn.bgcolor = ft.Colors.BLUE
                        btn.content = ft.Text("Save Score", color="white")
                        btn.disabled = False
                        try: page.update()
                        except: pass
                threading.Thread(target=revert).start()

            save_btn = ft.ElevatedButton(
                content=ft.Text("Save Score", color="white"),
                bgcolor=ft.Colors.BLUE,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                width=float("inf"),
                height=40,
                on_click=save_card
            )

            cards_registry[contestant.id] = {
                'btn': save_btn,
                'inputs': local_inputs,
                'info': {'name': contestant.name, 'gender': contestant.gender}
            }

            return ft.Container(
                width=320 if set_fixed_width else None, 
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, border_color),
                border_radius=12,
                shadow=ft.BoxShadow(blur_radius=4, color=ft.Colors.GREY_300),
                content=ft.Column([
                    ft.Container(
                        aspect_ratio=16/9, 
                        width=float("inf"), 
                        bgcolor=ft.Colors.GREY_300,
                        alignment=ft.alignment.center,
                        border_radius=ft.border_radius.only(top_left=12, top_right=12),
                        content=ft.Column([
                            ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=40, color="grey"), 
                            ft.Text("No Image", color="grey")
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=2)
                    ),
                    ft.Container(
                        padding=15,
                        content=ft.Column([
                            ft.Row([
                                ft.Container(content=ft.Text(f"#{contestant.candidate_number}", weight="bold", color="white"), bgcolor="black", padding=5, border_radius=5),
                                ft.Text(contestant.name, weight="bold", size=16, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ]),
                            ft.Divider(height=15),
                            inputs_column,
                            ft.Container(height=10),
                            save_btn
                        ])
                    )
                ], spacing=0)
            )

        # 5. ASSEMBLY
        rebuild_view(0)

        # Top Control Bar (Unified Row)
        top_bar = ft.Container(
            padding=10,
            content=ft.Row([
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: load_event_selector()),
                    segment_title,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Row([
                    gender_selector 
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN) 
        )

        main_container.content = ft.Column([
            top_bar,
            ft.Divider(height=1),
            content_area
        ], expand=True)
        page.update()

    load_event_selector()

    return ft.Column([header, main_container], expand=True)