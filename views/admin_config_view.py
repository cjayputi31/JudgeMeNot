import flet as ft
import shutil
import os
import time
from services.pageant_service import PageantService
from services.event_service import EventService
from services.contestant_service import ContestantService 
from services.export_service import ExportService 
from core.database import SessionLocal
from models.all_models import Event, Segment, Criteria, EventJudge

def AdminConfigView(page: ft.Page, event_id: int):
    # Services
    pageant_service = PageantService()
    event_service = EventService()
    contestant_service = ContestantService() 
    export_service = ExportService()

    from services.admin_service import AdminService
    admin_service = AdminService()

    # State
    current_event = None
    uploaded_file_path = None 

    # ---------------------------------------------------------
    # 1. FILE PICKER SETUP (DESKTOP MODE)
    # ---------------------------------------------------------
   
    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal uploaded_file_path
        if e.files:
            file_obj = e.files[0]
            
            # Check if we have a valid path (Desktop Mode)
            if file_obj.path:
                try:
                    # Create assets/uploads folder
                    os.makedirs("assets/uploads", exist_ok=True)
                    
                    # Generate unique filename
                    # Format: img_{timestamp}_{safe_name}
                    safe_name = "".join(x for x in file_obj.name if x.isalnum() or x in "._-")
                    new_filename = f"img_{int(time.time())}_{safe_name}"
                    dest_path = os.path.join("assets/uploads", new_filename)
                    
                    # COPY file locally
                    shutil.copy(file_obj.path, dest_path)
                    
                    # Store relative path for DB
                    uploaded_file_path = f"uploads/{new_filename}"
                    
                    # Update UI
                    img_preview.src = uploaded_file_path
                    img_preview.visible = True
                    img_preview.update()
                    
                    upload_btn.text = "Photo Selected"
                    upload_btn.icon = ft.Icons.CHECK
                    upload_btn.update()
                    
                    page.open(ft.SnackBar(ft.Text("Photo loaded successfully!"), bgcolor="green"))
                    
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"Error saving file: {ex}"), bgcolor="red"))
            else:
                # Fallback for Web Mode (Warning)
                page.open(ft.SnackBar(ft.Text("Browser Mode detected: Cannot upload files directly. Please run 'main.py' as a Desktop App."), bgcolor="orange"))

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # --- EXPORT PICKER ---
    def on_save_result(e: ft.FilePickerResultEvent):
        if e.path:
            scope_val = export_scope.value
            fmt = export_format.value

            if scope_val == "OVERALL":
                data = pageant_service.get_overall_breakdown(event_id)
                mode = "overall"
                title = "OVERALL TALLY SHEET"
            else:
                seg_id = int(scope_val)
                data = pageant_service.get_segment_tabulation(event_id, seg_id)
                mode = "segment"
            
                seg_name = next((opt.text for opt in export_scope.options if opt.key == scope_val), "Segment")
                title = f"SCORE SHEET: {seg_name.upper()}"

            try:
                if fmt == "excel":
                    export_service.generate_excel(e.path, current_event.name, title, data, mode)
                else:
                    export_service.generate_pdf(e.path, current_event.name, title, data, mode)

                page.open(ft.SnackBar(ft.Text("Export Successful!"), bgcolor="green"))
                page.close(export_dialog)
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"Export Failed: {ex}"), bgcolor="red"))

    save_file_picker = ft.FilePicker(on_result=on_save_result)
    

    page.overlay.append(save_file_picker)

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
    c_name = ft.TextField(label="Name", width=250)
    c_gender = ft.Dropdown(
        label="Gender", width=250,
        options=[ft.dropdown.Option("Female"), ft.dropdown.Option("Male")], 
        value="Female"
    )
    img_preview = ft.Image(width=100, height=100, fit=ft.ImageFit.COVER, visible=False, border_radius=10)
    upload_btn = ft.ElevatedButton("Upload Photo", icon=ft.Icons.UPLOAD, on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg"]))

    def add_contestant_click(e):
        nonlocal uploaded_file_path
        c_number.value = ""
        c_name.value = ""
        uploaded_file_path = None
        
        img_preview.visible = False
        img_preview.src = ""
        upload_btn.text = "Upload Photo"
        upload_btn.icon = ft.Icons.UPLOAD
        page.open(add_c_dialog)

    def save_contestant(e):
        if not c_number.value or not c_name.value:
            page.open(ft.SnackBar(ft.Text("Fill Number and Name"), bgcolor="red"))
            return
        try:
            num = int(c_number.value)
            success, msg = contestant_service.add_contestant(
                event_id, num, c_name.value, c_gender.value, uploaded_file_path
            )
            if success:
                page.open(ft.SnackBar(ft.Text("Contestant Added!"), bgcolor="green"))
                page.close(add_c_dialog)
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Number must be an integer"), bgcolor="red"))

    add_c_dialog = ft.AlertDialog(
        title=ft.Text("Add Contestant"),
        content=ft.Column([
            ft.Row([c_number, c_gender]),
            c_name,
            ft.Row([upload_btn, img_preview], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], height=250, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_contestant)]
    )

    def render_contestant_tab():
        contestants = contestant_service.get_contestants(event_id)
        males = [c for c in contestants if c.gender == "Male"]
        females = [c for c in contestants if c.gender == "Female"]

        def create_list_tile(c, color, icon):
            return ft.Container(
                padding=10,
                bgcolor=color,
                border_radius=10,
                content=ft.Row([
                    ft.Row([
                        # FIX: ALWAYS SHOW ICON IN ADMIN LIST
                        ft.Container(
                            width=40, height=40, border_radius=20,
                            content=ft.Icon(icon, color="white"), # <--- Always Icon
                            bgcolor="grey",
                            alignment=ft.alignment.center,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE
                        ),
                        ft.Container(
                            content=ft.Text(f"#{c.candidate_number}", size=14, weight="bold", color="white"),
                            bgcolor="black", padding=5, border_radius=5
                        ),
                        ft.Text(c.name, size=16, weight="bold")
                    ]),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", data=c.id, on_click=delete_contestant_click)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

        col_male = ft.Column(expand=True, scroll="hidden", spacing=10)
        col_male.controls.append(ft.Container(content=ft.Text("MALE CANDIDATES", weight="bold", color="blue"), padding=10))
        if not males: col_male.controls.append(ft.Text("No male candidates.", italic=True))
        for c in males:
            col_male.controls.append(create_list_tile(c, ft.Colors.BLUE_50, ft.Icons.MAN))

        col_female = ft.Column(expand=True, scroll="hidden", spacing=10)
        col_female.controls.append(ft.Container(content=ft.Text("FEMALE CANDIDATES", weight="bold", color="pink"), padding=10))
        if not females: col_female.controls.append(ft.Text("No female candidates.", italic=True))
        for c in females:
            col_female.controls.append(create_list_tile(c, ft.Colors.PINK_50, ft.Icons.WOMAN))

        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Manage Participants", size=20, weight="bold"),
                    ft.ElevatedButton("Add Candidate", icon=ft.Icons.ADD, on_click=add_contestant_click)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Row([
                    ft.Container(col_male, expand=True),
                    ft.VerticalDivider(width=1),
                    ft.Container(col_female, expand=True)
                ], expand=True)
            ], expand=True)
        )

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
    pending_action_seg_id = None 

    def on_final_check(e):
        p_qualifiers.visible = p_is_final.value
        p_seg_weight.disabled = p_is_final.value 
        if p_is_final.value: p_seg_weight.value = "100" 
        page.update()
    p_is_final.on_change = on_final_check

    # --- SAFETY DIALOGS ---
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

    confirm_input = ft.TextField(label="Type CONFIRM", border_color="red")
    confirm_btn = ft.ElevatedButton("Proceed", bgcolor="red", color="white", disabled=True)

    def validate_strict_input(e):
        text = confirm_input.value.strip().upper()
        is_valid = (text == "CONFIRM")
        confirm_btn.disabled = not is_valid
        confirm_btn.bgcolor = ft.Colors.RED if is_valid else ft.Colors.GREY
        confirm_btn.update()

    def confirm_strict_action(e):
        execute_toggle(pending_action_seg_id)
        page.close(strict_dialog)
        confirm_input.value = ""

    confirm_btn.on_click = confirm_strict_action
    confirm_input.on_change = validate_strict_input

    strict_dialog = ft.AlertDialog(
        title=ft.Row([ft.Icon(ft.Icons.WARNING, color="red"), ft.Text("Warning: Disruptive Action")]),
        content=ft.Column([
            ft.Text("You are about to deactivate or swap the active segment."),
            ft.Text("Warning: The judge might not be finished plotting scores.", color="red", weight="bold"),
            ft.Container(height=10),
            ft.Text("Type 'CONFIRM' to proceed:", size=12, weight="bold"),
            confirm_input
        ], tight=True, width=400),
        actions=[ft.TextButton("Cancel", on_click=lambda e: page.close(strict_dialog)), confirm_btn]
    )

    def request_toggle_status(seg_id):
        nonlocal pending_action_seg_id
        pending_action_seg_id = seg_id
        active_seg = event_service.get_active_segment(event_id)

        db = SessionLocal()
        all_segs = db.query(Segment).filter(Segment.event_id == event_id).all()
        final_is_active = any(s.is_active and s.is_final for s in all_segs)
        active_obj = next((s for s in all_segs if s.is_active), None)
        db.close()

        if final_is_active and seg_id is not None:
             if active_obj and active_obj.id == seg_id: pass
             else:
                 page.open(ft.SnackBar(ft.Text("Cannot switch segments while Final Round is active! Deactivate Final Round first."), bgcolor="red"))
                 return

        if seg_id is None: 
            if not active_seg: return
            page.open(strict_dialog)
            return
        if active_seg and active_seg.id != seg_id: 
            page.open(strict_dialog)
            return
        if active_seg and active_seg.id == seg_id: 
             page.open(strict_dialog)
             return
        page.open(simple_dialog) 

    def execute_toggle(seg_id):
        success, msg = event_service.set_active_segment(event_id, seg_id)
        if success:
            page.open(ft.SnackBar(ft.Text(msg), bgcolor="green"))
            refresh_ui()
        else:
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    # --- FINAL ROUND DIALOG ---
    final_confirm_input = ft.TextField(label="Type CONFIRM", border_color="red")
    final_confirm_btn = ft.ElevatedButton("ACTIVATE FINAL ROUND", bgcolor="grey", color="white", disabled=True)

    def validate_final_input(e):
        final_confirm_btn.disabled = (final_confirm_input.value != "CONFIRM")
        final_confirm_btn.bgcolor = "red" if final_confirm_input.value == "CONFIRM" else "grey"
        final_confirm_btn.update()

    def request_final_activation(seg_id):
        db = SessionLocal()
        seg = db.query(Segment).get(seg_id)
        limit = seg.qualifier_limit
        db.close()

        rankings = pageant_service.get_preliminary_rankings(event_id)
        qualifiers_controls = []
        eliminated_controls = []

        def build_list(rank_list, title):
            if rank_list:
                qualifiers_controls.append(ft.Text(f"--- {title} ---", color="blue", weight="bold"))
                eliminated_controls.append(ft.Text(f"--- {title} ---", color="blue", weight="bold"))
                for i, r in enumerate(rank_list):
                    rank = i + 1
                    line = f"#{rank} {r['contestant'].name} ({r['score']}%)"
                    if i < limit:
                        qualifiers_controls.append(ft.Text(line, weight="bold", color="green"))
                    else:
                        eliminated_controls.append(ft.Text(line, color="grey"))

        build_list(rankings['Male'], "MALE")
        build_list(rankings['Female'], "FEMALE")

        if not qualifiers_controls:
            qualifiers_controls.append(ft.Text("No scores recorded yet.", italic=True, color="orange"))

        final_confirm_input.value = ""
        final_confirm_input.on_change = validate_final_input
        final_confirm_btn.disabled = True
        final_confirm_btn.bgcolor = "grey"

        dlg = ft.AlertDialog(
            title=ft.Text("FINAL ROUND ACTIVATION"),
            content=ft.Column([
                ft.Text(f"Activating this will ELIMINATE candidates below Rank {limit}.", color="red", weight="bold"),
                ft.Divider(),
                ft.Text(f"QUALIFIERS (Top {limit}):", weight="bold"),
                ft.Column(controls=qualifiers_controls, spacing=2), 
                ft.Divider(),
                ft.Text("ELIMINATED:", weight="bold"),
                ft.Column(controls=eliminated_controls, spacing=2),
                ft.Divider(),
                ft.Text("Type 'CONFIRM' to proceed:", size=12, weight="bold"),
                final_confirm_input
            ], scroll="adaptive", height=400, width=500),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
                final_confirm_btn
            ]
        )

        final_confirm_btn.on_click = lambda e: execute_final_activation(seg_id, limit, dlg)
        page.open(dlg)

    def execute_final_activation(seg_id, limit, dlg):
        success, q, e = pageant_service.activate_final_round(event_id, seg_id, limit)
        page.close(dlg)
        if success:
            page.open(ft.SnackBar(ft.Text(f"Final Round Active! {len(q)} Qualified."), bgcolor="green"))
            refresh_ui()
        else:
            page.open(ft.SnackBar(ft.Text("Error activating round."), bgcolor="red"))

    # --- UI RENDERER ---
    def render_pageant_ui():
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).all()

        final_round_is_active = any(s.is_active and s.is_final for s in segments)

        ui_column = ft.Column(spacing=20, scroll="adaptive")

        ui_column.controls.append(ft.Row([
            ft.Text("Pageant Configuration", size=24, weight="bold"),
            ft.Row([
                ft.OutlinedButton("Deactivate All", icon=ft.Icons.STOP_CIRCLE, style=ft.ButtonStyle(color="red"), on_click=lambda e: request_toggle_status(None)),
                ft.ElevatedButton("Add Segment", icon=ft.Icons.ADD, on_click=open_add_seg_dialog)
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        current_total_weight = 0.0

        for seg in segments:
            if not seg.is_final:
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

            if seg.is_active:
                status_color = ft.Colors.GREEN_50
                status_text = "ACTIVE"
                status_icon = ft.Icons.RADIO_BUTTON_CHECKED
                border_side = ft.border.all(2, ft.Colors.GREEN)
                opacity = 1.0
                is_disabled = False 
            else:
                status_color = ft.Colors.WHITE
                status_text = "INACTIVE"
                status_icon = ft.Icons.RADIO_BUTTON_UNCHECKED
                border_side = None

                if final_round_is_active:
                    opacity = 0.5 
                    is_disabled = True 
                else:
                    opacity = 1.0
                    is_disabled = False

            if seg.is_final:
                card_bg = ft.Colors.AMBER_50 if seg.is_active else ft.Colors.GREY_100
                badge = ft.Container(content=ft.Text(f"FINAL (Top {seg.qualifier_limit})", color="black", size=12, weight="bold"), bgcolor=ft.Colors.AMBER_300, padding=5, border_radius=5)
            else:
                card_bg = status_color
                badge = ft.Chip(label=ft.Text(f"{int(seg.percentage_weight * 100)}%"))

            card = ft.Card(
                content=ft.Container(
                    bgcolor=card_bg,
                    border=border_side,
                    opacity=opacity,
                    padding=15,
                    content=ft.Column([
                        ft.Row([
                            ft.Row([
                                ft.IconButton(
                                    icon=status_icon, 
                                    icon_color="green" if seg.is_active else "grey",
                                    data=seg.id,
                                    disabled=is_disabled,
                                    on_click=lambda e, s=seg: request_final_activation(s.id) if s.is_final else request_toggle_status(s.id)
                                ),
                                ft.Text(f"{seg.name}", size=18, weight="bold"),
                                badge,
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

        if current_total_weight > 1.0001:
            ui_column.controls.append(ft.Text(f"⚠️ Prelim Weight is {int(current_total_weight*100)}%. It should be 100%.", color="red"))
        elif current_total_weight < 0.999:
            ui_column.controls.append(ft.Text(f"ℹ️ Prelim Weight is {int(current_total_weight*100)}%. Add more segments.", color="blue"))
        else:
             ui_column.controls.append(ft.Text("✅ Prelim Weight is 100%.", color="green"))

        db.close()
        return ft.Container(content=ui_column, padding=20)

    # --- SAVE HANDLERS ---
    def save_segment(e):
        try:
            if not p_is_final.value:
                raw_val = float(p_seg_weight.value)
                w = raw_val / 100.0 if raw_val > 1.0 else raw_val
            else:
                w = 0 
            limit = int(p_qualifiers.value) if p_is_final.value else 0

            if editing_segment_id:
                success, msg = event_service.update_segment(editing_segment_id, p_seg_name.value, w, p_is_final.value, limit)
            else:
                success, msg = event_service.add_segment(event_id, p_seg_name.value, w, 1, p_is_final.value, limit)

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
            w = raw_val / 100.0 if raw_val > 1.0 else raw_val
            if editing_criteria_id:
                success, msg = pageant_service.update_criteria(editing_criteria_id, p_crit_name.value, w)
            else:
                success, msg = pageant_service.add_criteria(selected_segment_id, p_crit_name.value, w)

            if success:
                page.open(ft.SnackBar(ft.Text("Saved!"), bgcolor="green"))
                page.close(crit_dialog)
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red"))

    seg_dialog = ft.AlertDialog(
        title=ft.Text("Segment Details"),
        content=ft.Column([p_seg_name, p_is_final, p_qualifiers, p_seg_weight], height=250, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_segment)]
    )
    crit_dialog = ft.AlertDialog(
        title=ft.Text("Criteria Details"),
        content=ft.Column([p_crit_name, p_crit_weight], height=150, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_criteria)]
    )

    def open_add_seg_dialog(e):
        nonlocal editing_segment_id
        editing_segment_id = None 
        p_seg_name.value = ""
        p_seg_weight.value = ""
        p_is_final.value = False
        on_final_check(None)
        seg_dialog.title.value = "Add Segment"
        page.open(seg_dialog)

    def open_edit_seg_dialog(e):
        nonlocal editing_segment_id
        seg_data = e.control.data
        editing_segment_id = seg_data.id 
        p_seg_name.value = seg_data.name
        p_seg_weight.value = str(int(seg_data.percentage_weight * 100))
        p_is_final.value = seg_data.is_final
        p_qualifiers.value = str(seg_data.qualifier_limit)
        on_final_check(None)
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
    # 5. JUDGE ASSIGNMENT TAB
    # ---------------------------------------------------------
    j_select = ft.Dropdown(label="Select Judge", width=300)
    j_is_chairman = ft.Checkbox(label="Is Chairman?", value=False)

    def load_judge_options():
        all_judges = admin_service.get_all_judges()
        j_select.options = [ft.dropdown.Option(text=j.name, key=str(j.id)) for j in all_judges]

    def add_judge_click(e):
        if not j_select.value:
            page.open(ft.SnackBar(ft.Text("Please select a judge"), bgcolor="red"))
            return
        judge_id = int(j_select.value)
        success, msg = event_service.assign_judge(event_id, judge_id, j_is_chairman.value)
        if success:
            page.open(ft.SnackBar(ft.Text(msg), bgcolor="green"))
            page.close(assign_judge_dialog) 
            refresh_ui()
        else:
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    assign_judge_dialog = ft.AlertDialog(
        title=ft.Text("Assign Judge"),
        content=ft.Column([
            j_select,
            j_is_chairman
        ], height=150, width=300, tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(assign_judge_dialog)),
            ft.ElevatedButton("Assign", on_click=add_judge_click)
        ]
    )

    def open_assign_judge_dialog(e):
        j_select.value = None
        j_is_chairman.value = False
        load_judge_options() 
        page.open(assign_judge_dialog)

    def remove_judge_click(e):
        assign_id = e.control.data
        success, msg = event_service.remove_judge(assign_id)
        if success:
            page.open(ft.SnackBar(ft.Text("Judge removed"), bgcolor="green"))
            refresh_ui()

    def render_judges_tab():
        assigned = event_service.get_assigned_judges(event_id)

        list_column = ft.Column(spacing=10, scroll="adaptive", expand=True) 

        for entry in assigned:
            role_text = "Chairman" if entry.is_chairman else "Judge"
            role_color = "orange" if entry.is_chairman else "blue"
            card = ft.Container(
                padding=10, 
                bgcolor=ft.Colors.GREY_50, 
                border_radius=10, 
                content=ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.GAVEL, color=role_color), 
                        ft.Text(entry.judge.name, size=16, weight="bold"), 
                        ft.Container(content=ft.Text(role_text, color="white", size=10), bgcolor=role_color, padding=5, border_radius=5)
                    ]), 
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", data=entry.id, on_click=remove_judge_click)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
            list_column.controls.append(card)

        if not assigned: 
            list_column.controls.append(ft.Text("No judges assigned yet.", italic=True, color="grey"))

        return ft.Container(
            padding=20, 
            content=ft.Column([
                ft.Row([
                    ft.Text("Assigned Judges", size=20, weight="bold"), 
                    ft.ElevatedButton("Assign Judge", icon=ft.Icons.ADD, on_click=open_assign_judge_dialog)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                ft.Divider(), 
                list_column
            ], expand=True)
        )

    # ---------------------------------------------------------
    # 6. EXPORT & TABULATION
    # ---------------------------------------------------------
    export_format = ft.RadioGroup(content=ft.Row([
        ft.Radio(value="pdf", label="PDF (with Signatures)"),
        ft.Radio(value="excel", label="Excel Spreadsheet")
    ]), value="pdf")

    export_scope = ft.Dropdown(label="Select Scope", width=300)

    def on_save_result(e: ft.FilePickerResultEvent):
        if e.path:
            scope_val = export_scope.value
            fmt = export_format.value

            if scope_val == "OVERALL":
                data = pageant_service.get_overall_breakdown(event_id)
                mode = "overall"
                title = "OVERALL TALLY SHEET"
            else:
                seg_id = int(scope_val)
                data = pageant_service.get_segment_tabulation(event_id, seg_id)
                mode = "segment"
                seg_name = next((opt.text for opt in export_scope.options if opt.key == scope_val), "Segment")
                title = f"SCORE SHEET: {seg_name.upper()}"

            try:
                if fmt == "excel":
                    export_service.generate_excel(e.path, current_event.name, title, data, mode)
                else:
                    export_service.generate_pdf(e.path, current_event.name, title, data, mode)

                page.open(ft.SnackBar(ft.Text("Export Successful!"), bgcolor="green"))
                page.close(export_dialog)
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"Export Failed: {ex}"), bgcolor="red"))

    save_file_picker = ft.FilePicker(on_result=on_save_result)
    page.overlay.append(save_file_picker)

    def initiate_export(e):
        if not export_scope.value:
            page.open(ft.SnackBar(ft.Text("Please select what to export"), bgcolor="red"))
            return

        scope_key = export_scope.value
        scope_name = "Overall"
        if scope_key != "OVERALL":
            for opt in export_scope.options:
                if opt.key == scope_key:
                    scope_name = opt.text
                    break
        
        safe_name = scope_name.replace(" ", "_")
        ext = "xlsx" if export_format.value == "excel" else "pdf"
        fname = f"{current_event.name}_{safe_name}.{ext}"

        save_file_picker.save_file(dialog_title="Save Score Sheet", file_name=fname)

    export_dialog = ft.AlertDialog(
        title=ft.Text("Export Scores"),
        content=ft.Column([
            ft.Text("Select Data Source:"),
            export_scope,
            ft.Divider(),
            ft.Text("Select Format:"),
            export_format
        ], height=200, width=350, tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(export_dialog)),
            ft.ElevatedButton("Export", icon=ft.Icons.DOWNLOAD, on_click=initiate_export)
        ]
    )

    def open_export_dialog(e):
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        db.close()

        opts = [ft.dropdown.Option(key="OVERALL", text="Overall Tally")]
        for s in segments:
            opts.append(ft.dropdown.Option(key=str(s.id), text=s.name))

        export_scope.options = opts
        export_scope.value = "OVERALL"
        page.open(export_dialog)

    def render_scores_tab():
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        db.close()

        def build_segment_table(gender_data, judges, title, color):
            cols = [
                ft.DataColumn(ft.Text("Rank"), numeric=True),
                ft.DataColumn(ft.Text("#"), numeric=True),
                ft.DataColumn(ft.Text("Candidate")),
            ]
            for j_name in judges:
                cols.append(ft.DataColumn(ft.Text(j_name, size=12, weight="bold"), numeric=True))
            cols.append(ft.DataColumn(ft.Text("Average"), numeric=True))

            rows = []
            for r in gender_data:
                cells = [
                    ft.DataCell(ft.Text(str(r['rank']), weight="bold")),
                    ft.DataCell(ft.Text(str(r['number']))),
                    ft.DataCell(ft.Text(r['name'], weight="bold" if r['rank']<=3 else "normal")),
                ]
                for score in r['scores']:
                    cells.append(ft.DataCell(ft.Text(str(score))))
                cells.append(ft.DataCell(ft.Text(str(r['total']), weight="bold", color="green")))
                rows.append(ft.DataRow(cells=cells))

            return ft.Column([
                ft.Container(content=ft.Text(title, weight="bold", color="white"), bgcolor=color, padding=10, border_radius=5, alignment=ft.alignment.center),
                ft.DataTable(columns=cols, rows=rows, column_spacing=20, heading_row_height=40)
            ], expand=True, scroll="adaptive")

        def build_overall_table(gender_data, segment_names, title, color):
            cols = [
                ft.DataColumn(ft.Text("Rank"), numeric=True),
                ft.DataColumn(ft.Text("#"), numeric=True),
                ft.DataColumn(ft.Text("Candidate")),
            ]
            for seg_name in segment_names:
                cols.append(ft.DataColumn(ft.Text(seg_name, size=12, weight="bold"), numeric=True))
            cols.append(ft.DataColumn(ft.Text("Total %"), numeric=True))

            rows = []
            for r in gender_data:
                cells = [
                    ft.DataCell(ft.Text(str(r['rank']), weight="bold")),
                    ft.DataCell(ft.Text(str(r['number']))),
                    ft.DataCell(ft.Text(r['name'], weight="bold" if r['rank']<=3 else "normal")),
                ]
                for score in r['segment_scores']:
                    cells.append(ft.DataCell(ft.Text(str(score))))
                cells.append(ft.DataCell(ft.Text(str(r['total']), weight="bold", color="green")))
                rows.append(ft.DataRow(cells=cells))

            return ft.Column([
                ft.Container(content=ft.Text(title, weight="bold", color="white"), bgcolor=color, padding=10, border_radius=5, alignment=ft.alignment.center, width=float("inf")),
                ft.DataTable(columns=cols, rows=rows, column_spacing=20, heading_row_height=40, width=float("inf"))
            ], expand=True, scroll="adaptive")

        def get_tab_content(seg_id=None):
            if seg_id is None:
                matrix = pageant_service.get_overall_breakdown(event_id)
                seg_names = matrix['segments']
                male_table = build_overall_table(matrix['Male'], seg_names, "MALE OVERALL STANDING", ft.Colors.BLUE)
                female_table = build_overall_table(matrix['Female'], seg_names, "FEMALE OVERALL STANDING", ft.Colors.PINK)
                return ft.Container(padding=10, content=ft.Column([male_table, ft.Divider(), female_table], scroll="adaptive", expand=True))
            else:
                matrix = pageant_service.get_segment_tabulation(event_id, seg_id)
                judges = matrix['judges']
                male_col = build_segment_table(matrix['Male'], judges, "MALE RANKING", ft.Colors.BLUE)
                female_col = build_segment_table(matrix['Female'], judges, "FEMALE RANKING", ft.Colors.PINK)
                return ft.Container(padding=10, content=ft.Row([male_col, ft.VerticalDivider(width=1), female_col], expand=True))

        score_tabs = [
            ft.Tab(text="OVERALL TALLY", icon=ft.Icons.ASSESSMENT, content=get_tab_content(None))
        ]
        for s in segments:
            score_tabs.append(ft.Tab(text=s.name.upper(), content=get_tab_content(s.id)))

        return ft.Container(
            padding=0,
            content=ft.Column([
                ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Text("Live Tabulation Board", size=20, weight="bold"),
                        ft.Row([
                            ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Refresh Rankings", on_click=lambda e: refresh_ui()),
                            ft.ElevatedButton("Export Scores", icon=ft.Icons.DOWNLOAD, on_click=open_export_dialog)
                        ])
                    ], alignment="spaceBetween")
                ),
                ft.Tabs(tabs=score_tabs, animation_duration=300, expand=True, scrollable=True)
            ], expand=True)
        )

    # ---------------------------------------------------------
    # 7. QUIZ BEE (Minimal)
    # ---------------------------------------------------------
    q_round_name = ft.TextField(label="Round Name", width=280)
    q_points = ft.TextField(label="Points", width=280)
    q_total_qs = ft.TextField(label="Total Qs", width=280)

    round_dialog = ft.AlertDialog(title=ft.Text("Add Round"), content=ft.Column([q_round_name, q_points, q_total_qs], height=220, width=300, tight=True), actions=[ft.TextButton("Save", on_click=lambda e: save_round(e))])

    def render_quiz_ui():
        db = SessionLocal(); rounds = db.query(Segment).filter(Segment.event_id == event_id).all()
        col = ft.Column(spacing=20); col.controls.append(ft.Row([ft.Text("Quiz Bee", size=24, weight="bold"), ft.ElevatedButton("Add Round", on_click=lambda e: page.open(round_dialog))], alignment="spaceBetween"))
        for r in rounds: col.controls.append(ft.Card(content=ft.Container(padding=15, content=ft.Text(f"{r.name} ({r.points_per_question} pts)"))))
        db.close(); return ft.Container(content=col, padding=20)

    def save_round(e):
        try:
            pts = float(q_points.value); qs = int(q_total_qs.value); success, msg = quiz_service.add_round(event_id, q_round_name.value, pts, qs, 1)
            if success: page.open(ft.SnackBar(ft.Text("Round Added!"), bgcolor="green")); page.close(round_dialog); refresh_ui()
            else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except: page.open(ft.SnackBar(ft.Text("Invalid Input"), bgcolor="red"))

    # ---------------------------------------------------------
    # 8. MAIN ASSEMBLY
    # ---------------------------------------------------------
    def render_config_tab():
        if current_event.event_type == "Pageant": return render_pageant_ui()
        else: return render_quiz_ui()

    tabs = ft.Tabs(selected_index=0, animation_duration=300, tabs=[
        ft.Tab(text="Configuration", icon=ft.Icons.SETTINGS, content=render_config_tab()),
        ft.Tab(text="Contestants", icon=ft.Icons.PEOPLE, content=render_contestant_tab()),
        ft.Tab(text="Judges", icon=ft.Icons.GAVEL, content=render_judges_tab()),
        ft.Tab(text="Tabulation", icon=ft.Icons.LEADERBOARD, content=render_scores_tab()), 
    ], expand=True)

    def refresh_ui():
        tabs.tabs[0].content = render_config_tab(); tabs.tabs[1].content = render_contestant_tab(); tabs.tabs[2].content = render_judges_tab(); tabs.tabs[3].content = render_scores_tab(); page.update()
