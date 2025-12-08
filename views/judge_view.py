import flet as ft
from services.pageant_service import PageantService
from services.contestant_service import ContestantService
from services.event_service import EventService
import time, threading
from datetime import datetime
# IMPORT SHARED DIALOGS
from components.dialogs import show_about_dialog, show_contact_dialog

def JudgeView(page: ft.Page, on_logout_callback):
    # Services
    pageant_service = PageantService()
    contestant_service = ContestantService()
    event_service = EventService()

    judge_id = page.session.get("user_id")
    judge_name = page.session.get("user_name")
    current_event = None; selected_segment = None; cards_registry = {}
    is_polling = False; last_check_text = ft.Text("Initializing...", size=12, color="grey")
    main_container = ft.Container(expand=True, padding=10)

    # ---------------------------------------------------------
    # POLLING
    # ---------------------------------------------------------
    def start_polling():
        nonlocal is_polling; 
        if is_polling: return 
        is_polling = True; threading.Thread(target=poll_active_segment, daemon=True).start()
    def stop_polling(): nonlocal is_polling; is_polling = False
    def poll_active_segment():
        while is_polling and current_event:
            try:
                active_seg_db = pageant_service.get_active_segment(current_event.id)
                try: new_seg_id = active_seg_db.id if active_seg_db else None
                except: new_seg_id = None
                current_seg_id = selected_segment['segment'].id if selected_segment else None
                if last_check_text.page:
                    now = datetime.now().strftime("%H:%M:%S"); last_check_text.value = f"Last checked: {now}"; last_check_text.update()
                if new_seg_id != current_seg_id:
                    if page.dialog and page.dialog.open: page.close(page.dialog)
                    enter_scoring_dashboard(current_event)
            except: pass
            time.sleep(2)

    # ---------------------------------------------------------
    # HEADER & SUBMIT
    # ---------------------------------------------------------
    def show_waiting_room(title, msg):
        start_polling() 
        content = ft.Column([ft.ProgressRing(width=50, height=50), ft.Container(height=20), ft.Text(title, size=24, weight="bold"), ft.Text(msg, color="grey"), ft.Text("Screen will refresh automatically.", italic=True, color="blue"), last_check_text, ft.Container(height=20), ft.OutlinedButton("Manual Refresh", icon=ft.Icons.REFRESH, on_click=lambda e: enter_scoring_dashboard(current_event))], alignment="center", horizontal_alignment="center")
        main_container.content = ft.Column([ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: load_event_selector())]), ft.Container(content=content, alignment=ft.alignment.center, expand=True)], expand=True); page.update()

    def submit_final_scores(e):
        missing = []; unlocked = []
        for c_id, card_data in cards_registry.items():
            for ref in card_data['inputs'].values():
                if not ref['field'].value: missing.append(f"{card_data['info']['name']}"); break 
            if not card_data['get_locked_status'](): unlocked.append(f"{card_data['info']['name']}")

        errs = []
        if missing: errs.append(ft.Text("Missing scores:", color="red", weight="bold")); errs.extend([ft.Text(f"• {m}") for m in missing[:3]])
        if unlocked: errs.append(ft.Text("Not Locked:", color="orange", weight="bold")); errs.extend([ft.Text(f"• {u}") for u in unlocked[:3]])

        if errs: 
            error_dlg = ft.AlertDialog(
                title=ft.Text("Incomplete"), 
                content=ft.Column(errs, tight=True), 
                actions=[ft.TextButton("OK", on_click=lambda e: page.close(error_dlg))]
            )
            page.open(error_dlg)
            return

        def confirm_submission(e): 
            page.close(confirm_dlg)
            pageant_service.mark_judge_finished(judge_id, selected_segment['segment'].id)
            show_waiting_room("Scores Submitted!", "Waiting for next segment...")

        confirm_dlg = ft.AlertDialog(
            title=ft.Text("Confirm Submission"), 
            content=ft.Text("Are you sure? You cannot change scores after this."), 
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(confirm_dlg)), 
                ft.ElevatedButton("CONFIRM", bgcolor="green", color="white", on_click=confirm_submission)
            ]
        )
        page.open(confirm_dlg)

    submit_all_btn = ft.ElevatedButton("Submit Final Tally", icon=ft.Icons.PUBLISH, bgcolor=ft.Colors.GREEN_600, color="white", on_click=submit_final_scores)

    header = ft.Container(
        content=ft.Row([
            ft.Row([ft.Icon(ft.Icons.GAVEL, color="white"), ft.Column([ft.Text(f"Judge: {judge_name}", weight="bold", color="white"), ft.Text("Scoring Panel", size=12, color="white70")], spacing=2)]),
            # Updated Right Side with Leaderboard/About/Contact
            ft.Row([
                ft.TextButton("Leaderboard", icon=ft.Icons.EMOJI_EVENTS, style=ft.ButtonStyle(color=ft.Colors.WHITE), on_click=lambda e: page.go("/leaderboard")),
                ft.TextButton("About", style=ft.ButtonStyle(color=ft.Colors.WHITE), on_click=lambda e: show_about_dialog(page)),
                ft.TextButton("Contact", style=ft.ButtonStyle(color=ft.Colors.WHITE), on_click=lambda e: show_contact_dialog(page)),
                ft.VerticalDivider(width=10, color="white24"),
                submit_all_btn,
                ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="white", on_click=on_logout_callback)
            ])
        ], alignment="spaceBetween"),
        padding=15, bgcolor=ft.Colors.BLUE_800
    )

    # ---------------------------------------------------------
    # MAIN LOGIC (Event Load, Dashboard)
    # ---------------------------------------------------------
    def load_event_selector():
        stop_polling()
        submit_all_btn.disabled = True; submit_all_btn.update() if submit_all_btn.page else None
        events = event_service.get_judge_events(judge_id)
        if not events: main_container.content = ft.Column([ft.Icon(ft.Icons.EVENT_BUSY, size=60, color="grey"), ft.Text("No active events found.", size=20, color="grey"), ft.ElevatedButton("Refresh", on_click=lambda e: load_event_selector())], alignment="center", horizontal_alignment="center"); page.update(); return

        grid = ft.GridView(expand=True, max_extent=300, spacing=20, run_spacing=20)
        for e in events: grid.controls.append(ft.Container(bgcolor="white", border_radius=15, padding=20, shadow=ft.BoxShadow(blur_radius=10, color="grey"), content=ft.Column([ft.Icon(ft.Icons.STAR_ROUNDED, size=50, color="orange"), ft.Text(e.name, weight="bold", size=18, text_align="center"), ft.Text(f"Status: {e.status}", color="green"), ft.ElevatedButton("Start Judging", on_click=lambda x, ev=e: enter_scoring_dashboard(ev))], alignment="center", horizontal_alignment="center"), on_click=lambda x, ev=e: enter_scoring_dashboard(ev)))
        main_container.content = ft.Column([ft.Text("Select Active Event", size=24, weight="bold"), ft.Divider(), grid], expand=True); page.update()

    def enter_scoring_dashboard(event):
        nonlocal current_event, selected_segment; current_event = event
        if not event_service.is_judge_assigned(judge_id, event.id): page.open(ft.SnackBar(ft.Text("Access Denied"), bgcolor="red")); return

        active_seg = pageant_service.get_active_segment(current_event.id)
        if not active_seg: selected_segment = None; show_waiting_room("Waiting for Admin...", "No segment is currently active."); return
        if pageant_service.has_judge_finished(judge_id, active_seg.id): selected_segment = {'segment': active_seg}; show_waiting_room("Scores Submitted!", "You have already scored this segment."); return

        structure = pageant_service.get_event_structure(current_event.id)
        target_struct = next((s for s in structure if s['segment'].id == active_seg.id), None)
        if target_struct: selected_segment = target_struct; render_dashboard(target_struct); start_polling(); submit_all_btn.disabled = False; submit_all_btn.update()
        else: page.open(ft.SnackBar(ft.Text("Error loading data"), bgcolor="red"))

    def render_dashboard(structure_item):
        segment_title = ft.Text(f"{structure_item['segment'].name}", size=20, weight="bold", color=ft.Colors.BLUE_800)
        refresh_btn = ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Force Refresh", on_click=lambda e: enter_scoring_dashboard(current_event))
        gender_selector = ft.SegmentedButton(selected={"0"}, segments=[ft.Segment(value="0", label=ft.Text("All"), icon=ft.Icon(ft.Icons.GROUPS)), ft.Segment(value="1", label=ft.Text("Female"), icon=ft.Icon(ft.Icons.WOMAN)), ft.Segment(value="2", label=ft.Text("Male"), icon=ft.Icon(ft.Icons.MAN))], on_change=lambda e: rebuild_view(int(list(e.control.selected)[0])))
        content_area = ft.Container(expand=True)

        def rebuild_view(tab_index):
            cards_registry.clear(); candidates = contestant_service.get_contestants(current_event.id, active_only=True)
            def get_cards(gender): return [create_scoring_card(c, pageant_service.get_judge_scores(judge_id, c.id)) for c in candidates if c.gender == gender]

            if tab_index == 0: 
                # FIX: Removed the extra wrapper Column and used direct placement in Row
                # This prevents the 'expand' properties from conflicting and hiding content
                col_male = ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Text("Male Candidates", weight="bold", color="blue"), 
                            bgcolor=ft.Colors.BLUE_50, 
                            padding=10, 
                            border_radius=5, 
                            alignment=ft.alignment.center, 
                            width=380
                        )
                    ] + get_cards("Male"), 
                    expand=True, 
                    scroll="hidden", 
                    spacing=15, 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )

                col_female = ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Text("Female Candidates", weight="bold", color="pink"), 
                            bgcolor=ft.Colors.PINK_50, 
                            padding=10, 
                            border_radius=5, 
                            alignment=ft.alignment.center, 
                            width=380
                        )
                    ] + get_cards("Female"), 
                    expand=True, 
                    scroll="hidden", 
                    spacing=15, 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )

                content_area.content = ft.Row(
                    controls=[
                        col_male, 
                        ft.VerticalDivider(width=1, color="grey"), 
                        col_female
                    ], 
                    expand=True
                )
            else: 
                target = "Female" if tab_index == 1 else "Male"; cards = get_cards(target)
                if not cards: content_area.content = ft.Column([ft.Icon(ft.Icons.SEARCH_OFF, size=50, color="grey"), ft.Text("No candidates found.", color="grey")], alignment="center", horizontal_alignment="center", expand=True)
                else: content_area.content = ft.Column([ft.Row(controls=cards, wrap=True, alignment="center", spacing=20)], scroll="adaptive", expand=True)
            page.update()

        def create_scoring_card(contestant, existing_scores):
            border_col = ft.Colors.BLUE_200 if contestant.gender == "Male" else ft.Colors.PINK_200
            inputs_column = ft.Column(spacing=5); local_inputs = {}; is_locked = False

            def toggle_lock(e):
                nonlocal is_locked; btn = e.control
                if not is_locked:
                    btn.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color="white"); btn.disabled = True; page.update(); valid = True
                    for crit_id, ref in local_inputs.items():
                        val_str = ref['field'].value; 
                        if not val_str: valid=False; ref['field'].border_color="red"; continue
                        try: val = float(val_str); 
                        except: valid=False; ref['field'].border_color="red"; continue
                        if val < 0 or val > ref['max']: valid=False; ref['field'].border_color="red"
                        else: ref['field'].border_color="green"; pageant_service.submit_score(judge_id, contestant.id, crit_id, val)
                    btn.disabled = False
                    if valid: is_locked = True; btn.bgcolor = ft.Colors.ORANGE; btn.content = ft.Row([ft.Icon(ft.Icons.LOCK, color="white", size=16), ft.Text("Unlock", color="white")], alignment="center"); [ setattr(ref['field'], 'read_only', True) or ref['field'].update() for ref in local_inputs.values()]
                    else: btn.bgcolor = ft.Colors.RED; btn.content = ft.Text("Error", color="white"); threading.Thread(target=lambda: (time.sleep(2), setattr(btn, 'bgcolor', ft.Colors.BLUE), setattr(btn, 'content', ft.Text("Lock & Save", color="white")), btn.update())).start()
                else: is_locked = False; btn.bgcolor = ft.Colors.BLUE; btn.content = ft.Text("Lock & Save", color="white"); [ setattr(ref['field'], 'read_only', False) or ref['field'].update() for ref in local_inputs.values()]
                page.update()

            def on_input_change(e):
                if not is_locked: btn = cards_registry[contestant.id]['btn']; 
                if btn.bgcolor != ft.Colors.BLUE: btn.bgcolor, btn.content = ft.Colors.BLUE, ft.Text("Lock & Save", color="white"); btn.update()

            for crit in structure_item['criteria']:
                val = existing_scores.get(crit.id, ""); tf = ft.TextField(value=str(val) if val!="" else "", width=70, height=30, text_size=14, content_padding=5, text_align="center", on_change=on_input_change)
                local_inputs[crit.id] = {"field": tf, "max": crit.max_score}
                inputs_column.controls.append(ft.Row([ft.Text(crit.name, size=14, weight="bold", expand=True, max_lines=1, overflow="ellipsis"), ft.Text(f"/{int(crit.max_score)} ({int(crit.weight*100)}%)", size=11, color="grey"), tf], alignment="spaceBetween"))

            save_btn = ft.ElevatedButton(content=ft.Text("Lock & Save", color="white", size=14), bgcolor=ft.Colors.BLUE, width=float("inf"), height=40, on_click=toggle_lock)
            cards_registry[contestant.id] = {'btn': save_btn, 'inputs': local_inputs, 'info': {'name': contestant.name, 'gender': contestant.gender}, 'get_locked_status': lambda: is_locked}
            img_content = ft.Image(src=contestant.image_path, fit=ft.ImageFit.COVER, error_content=ft.Icon(ft.Icons.BROKEN_IMAGE, size=40)) if contestant.image_path else ft.Column([ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=50, color="grey"), ft.Text("No Img", color="grey", size=12)], alignment="center", spacing=2)

            # CLEAN HORIZONTAL CARD
            return ft.Container(
                width=450, # Slightly wider for better fit
                bgcolor="white", 
                border=ft.border.all(1, border_col), 
                border_radius=10, 
                padding=10, 
                shadow=ft.BoxShadow(blur_radius=2, color="grey"), 
                content=ft.Row([
                    # Photo (Left)
                    ft.Container(
                        width=140, height=180, 
                        bgcolor=ft.Colors.GREY_200, 
                        border_radius=5, 
                        alignment=ft.alignment.center, 
                        clip_behavior=ft.ClipBehavior.HARD_EDGE, 
                        content=img_content
                    ), 
                    # Inputs (Right)
                    ft.Container(
                        expand=True, 
                        content=ft.Column([
                            ft.Row([
                                ft.Container(content=ft.Text(f"#{contestant.candidate_number}", weight="bold", color="white", size=16), bgcolor="black", padding=5, border_radius=4), 
                                ft.Text(contestant.name, weight="bold", size=16, expand=True, max_lines=2, overflow="ellipsis")
                            ], alignment="start", vertical_alignment="start"), 
                            ft.Divider(height=10, color="transparent"), 
                            inputs_column, 
                            ft.Container(height=10), 
                            save_btn
                        ])
                    )
                ], alignment="start", vertical_alignment="start")
            )

        rebuild_view(0)
        top_bar = ft.Container(padding=10, content=ft.Row([ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: load_event_selector()), ft.Text("Segment:", size=16, weight="bold"), segment_title]), ft.Row([refresh_btn, gender_selector])], alignment="spaceBetween"))
        main_container.content = ft.Column([top_bar, ft.Divider(height=1), content_area], expand=True); page.update()

    load_event_selector()