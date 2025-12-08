import flet as ft
import shutil
import os
import time
from services.pageant_service import PageantService
from services.event_service import EventService
from services.contestant_service import ContestantService
from services.admin_service import AdminService
from services.export_service import ExportService
from core.database import SessionLocal
from models.all_models import Segment, Criteria

def PageantConfigView(page: ft.Page, event_id: int):
    # Services
    pageant_service = PageantService()
    event_service = EventService()
    contestant_service = ContestantService()
    admin_service = AdminService()
    export_service = ExportService()

    # --- STATE VARIABLES ---
    # Config Tab State
    editing_segment_id = None 
    editing_criteria_id = None 
    selected_segment_id = None
    pending_action_seg_id = None

    # Contestant Tab State
    uploaded_file_path = None
    editing_contestant_id = None

    # --- UI WRAPPERS FOR TABS ---
    config_tab_content = ft.Column(spacing=20, scroll="adaptive", expand=True)
    contestant_tab_content = ft.Column(spacing=20, scroll="adaptive", expand=True)
    judges_tab_content = ft.Column(spacing=20, scroll="adaptive", expand=True)
    scores_tab_content = ft.Column(spacing=20, scroll="adaptive", expand=True)

    # =================================================================================================
    # TAB 1: CONFIGURATION (Merged from old pageant_config_view.py)
    # =================================================================================================
    
    # --- UI CONTROLS ---
    p_seg_name = ft.TextField(label="Segment Name", width=280)
    p_seg_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    p_crit_name = ft.TextField(label="Criteria Name", width=280)
    p_crit_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    p_is_final = ft.Checkbox(label="Is Final Round?", value=False)
    p_qualifiers = ft.TextField(label="Qualifiers Count", value="5", width=280, visible=False, keyboard_type=ft.KeyboardType.NUMBER)

    def on_final_check(e):
        p_qualifiers.visible = p_is_final.value
        p_seg_weight.disabled = p_is_final.value 
        if p_is_final.value: p_seg_weight.value = "100" 
        page.update()
    p_is_final.on_change = on_final_check

    # --- REFRESH LOGIC ---
    def refresh_config_tab():
        config_tab_content.controls.clear()

        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).all()
        final_round_is_active = any(s.is_active and s.is_final for s in segments)

        config_tab_content.controls.append(ft.Row([
            ft.Text("Pageant Rounds", size=20, weight="bold"),
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

            # STATUS LOGIC
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
            config_tab_content.controls.append(card)

        if current_total_weight > 1.0001:
            config_tab_content.controls.append(ft.Text(f"⚠️ Prelim Weight is {int(current_total_weight*100)}%. It should be 100%.", color="red"))
        elif current_total_weight < 0.999:
            config_tab_content.controls.append(ft.Text(f"ℹ️ Prelim Weight is {int(current_total_weight*100)}%. Add more segments.", color="blue"))
        else:
            config_tab_content.controls.append(ft.Text("✅ Prelim Weight is 100%.", color="green"))

        db.close()
        page.update()

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
                 page.open(ft.SnackBar(ft.Text("Cannot switch segments while Final Round is active!"), bgcolor="red"))
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
            refresh_config_tab()
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
                        qualifiers_controls.append(ft.Text(line, weight="bold", color="green", size=16))
                    else:
                        eliminated_controls.append(ft.Text(line, color="grey", size=14))

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
            refresh_config_tab()
        else:
            page.open(ft.SnackBar(ft.Text("Error activating round."), bgcolor="red"))

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
                refresh_config_tab()
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
                refresh_config_tab()
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

    # =================================================================================================
    # TAB 2: CONTESTANTS (With Male/Female Separation)
    # =================================================================================================
    c_number = ft.TextField(label="#", width=80, keyboard_type=ft.KeyboardType.NUMBER)
    c_name = ft.TextField(label="Name", width=250)
    c_gender = ft.Dropdown(label="Gender", width=250, options=[ft.dropdown.Option("Female"), ft.dropdown.Option("Male")], value="Female")
    img_preview = ft.Image(width=100, height=100, fit=ft.ImageFit.COVER, visible=False, border_radius=10)

    # File Picker Logic
    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal uploaded_file_path
        if e.files:
            try:
                os.makedirs("assets/uploads", exist_ok=True)
                file_obj = e.files[0]
                safe_name = f"img_{int(time.time())}_{file_obj.name}"
                shutil.copy(file_obj.path, os.path.join("assets/uploads", safe_name))
                uploaded_file_path = f"uploads/{safe_name}"
                img_preview.src = uploaded_file_path
                img_preview.visible = True
                img_preview.update()
            except Exception as ex: page.open(ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red"))

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)
    upload_btn = ft.ElevatedButton("Photo", icon=ft.Icons.UPLOAD, on_click=lambda _: file_picker.pick_files(allow_multiple=False))

    def save_contestant(e):
        if not c_number.value or not c_name.value: page.open(ft.SnackBar(ft.Text("Missing info"), bgcolor="red")); return
        try:
            num = int(c_number.value)
            if editing_contestant_id: success, msg = contestant_service.update_contestant(editing_contestant_id, num, c_name.value, c_gender.value, uploaded_file_path)
            else: success, msg = contestant_service.add_contestant(event_id, num, c_name.value, c_gender.value, uploaded_file_path)
            
            if success: page.open(ft.SnackBar(ft.Text("Saved!"), bgcolor="green")); page.close(contestant_dialog); refresh_contestant_tab()
            else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except: page.open(ft.SnackBar(ft.Text("Invalid Number"), bgcolor="red"))

    contestant_dialog = ft.AlertDialog(title=ft.Text("Contestant"), content=ft.Column([ft.Row([c_number, c_gender]), c_name, ft.Row([upload_btn, img_preview])], height=250, width=300), actions=[ft.TextButton("Save", on_click=save_contestant)])
    
    def open_add_c_dialog(e): nonlocal editing_contestant_id, uploaded_file_path; editing_contestant_id=None; uploaded_file_path=None; c_number.value=""; c_name.value=""; img_preview.visible=False; page.open(contestant_dialog)
    def open_edit_c_dialog(e): nonlocal editing_contestant_id, uploaded_file_path; d=e.control.data; editing_contestant_id=d.id; uploaded_file_path=d.image_path; c_number.value=str(d.candidate_number); c_name.value=d.name; c_gender.value=d.gender; img_preview.src=d.image_path if d.image_path else ""; img_preview.visible=bool(d.image_path); page.open(contestant_dialog)
    def delete_contestant(e): contestant_service.delete_contestant(e.control.data); refresh_contestant_tab()

    def refresh_contestant_tab():
        contestant_tab_content.controls.clear()
        contestants = contestant_service.get_contestants(event_id)
        
        contestant_tab_content.controls.append(ft.Row([ft.Text("Pageant Candidates", size=20, weight="bold"), ft.ElevatedButton("Add Candidate", icon=ft.Icons.ADD, on_click=open_add_c_dialog)], alignment="spaceBetween"))
        
        def build_list(gender, icon, color):
            items = [c for c in contestants if c.gender == gender]
            controls = [ft.Container(content=ft.Text(f"{gender.upper()} CANDIDATES", weight="bold", color=color), padding=5)]
            for c in items:
                controls.append(ft.Container(
                    padding=10, bgcolor=ft.Colors.with_opacity(0.1, color), border_radius=10,
                    content=ft.Row([
                        ft.Row([ft.Container(content=ft.Text(f"#{c.candidate_number}", color="white", weight="bold"), bgcolor="black", padding=5, border_radius=5), ft.Text(c.name, weight="bold")]),
                        ft.Row([ft.IconButton(icon=ft.Icons.EDIT, icon_color="blue", data=c, on_click=open_edit_c_dialog), ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", data=c.id, on_click=delete_contestant)])
                    ], alignment="spaceBetween")
                ))
            return ft.Column(controls, expand=True, scroll="hidden", spacing=5)

        contestant_tab_content.controls.append(ft.Row([
            ft.Container(build_list("Male", ft.Icons.MAN, "blue"), expand=True), 
            ft.VerticalDivider(), 
            ft.Container(build_list("Female", ft.Icons.WOMAN, "pink"), expand=True)
        ], expand=True))
        page.update()

    # =================================================================================================
    # TAB 3: JUDGES
    # =================================================================================================
    j_select = ft.Dropdown(label="Select Judge", width=300)
    j_is_chairman = ft.Checkbox(label="Is Chairman?", value=False)
    
    def save_judge(e):
        if not j_select.value: return
        success, msg = event_service.assign_judge(event_id, int(j_select.value), j_is_chairman.value)
        if success: page.open(ft.SnackBar(ft.Text(msg), bgcolor="green")); page.close(judge_dialog); refresh_judges_tab()
        else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

    judge_dialog = ft.AlertDialog(title=ft.Text("Assign Judge"), content=ft.Column([j_select, j_is_chairman], height=150, width=300), actions=[ft.TextButton("Assign", on_click=save_judge)])
    
    def open_judge_dialog(e):
        users = admin_service.get_all_judges()
        j_select.options = [ft.dropdown.Option(key=str(u.id), text=u.name) for u in users]
        page.open(judge_dialog)

    def remove_judge(e): event_service.remove_judge(e.control.data); refresh_judges_tab()

    def refresh_judges_tab():
        judges_tab_content.controls.clear()
        judges_tab_content.controls.append(ft.Row([ft.Text("Panel of Judges", size=20, weight="bold"), ft.ElevatedButton("Assign Judge", icon=ft.Icons.ADD, on_click=open_judge_dialog)], alignment="spaceBetween"))
        
        assigned = event_service.get_assigned_judges(event_id)
        for aj in assigned:
            role_col = "orange" if aj.is_chairman else "blue"
            judges_tab_content.controls.append(ft.Container(
                padding=10, bgcolor=ft.Colors.GREY_50, border_radius=10,
                content=ft.Row([
                    ft.Row([ft.Icon(ft.Icons.GAVEL, color=role_col), ft.Text(aj.judge.name, weight="bold"), ft.Chip(label=ft.Text("Chairman" if aj.is_chairman else "Judge"))]),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", data=aj.id, on_click=remove_judge)
                ], alignment="spaceBetween")
            ))
        page.update()

    # =================================================================================================
    # TAB 4: TABULATION
    # =================================================================================================
    def refresh_scores_tab():
        scores_tab_content.controls.clear()
        
        # Header with Export
        scores_tab_content.controls.append(ft.Row([
            ft.Text("Tabulation Board", size=20, weight="bold"),
            ft.Row([
                ft.IconButton(icon=ft.Icons.REFRESH, on_click=lambda e: refresh_scores_tab()),
                ft.ElevatedButton("Export Scores", icon=ft.Icons.DOWNLOAD, on_click=lambda e: page.open(ft.SnackBar(ft.Text("Export logic moved to ExportService"), bgcolor="blue")))
            ])
        ], alignment="spaceBetween"))

        # Tabs for Segments
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        db.close()

        def build_matrix(seg_id):
            if seg_id is None: # Overall
                data = pageant_service.get_overall_breakdown(event_id)
                cols = ["Rank", "#", "Name"] + data['segments'] + ["Total"]
                rows = []
                for gender in ['Male', 'Female']:
                    rows.append(ft.DataRow([ft.DataCell(ft.Text(f"-- {gender.upper()} --", weight="bold", color="blue"))] + [ft.DataCell(ft.Text(""))]*(len(cols)-1)))
                    for r in data[gender]:
                        cells = [ft.DataCell(ft.Text(str(r['rank']))), ft.DataCell(ft.Text(str(r['number']))), ft.DataCell(ft.Text(r['name']))]
                        for s in r['segment_scores']: cells.append(ft.DataCell(ft.Text(str(s))))
                        cells.append(ft.DataCell(ft.Text(str(r['total']), weight="bold", color="green")))
                        rows.append(ft.DataRow(cells))
            else: # Segment
                data = pageant_service.get_segment_tabulation(event_id, seg_id)
                cols = ["Rank", "#", "Name"] + data['judges'] + ["Average"]
                rows = []
                for gender in ['Male', 'Female']:
                    rows.append(ft.DataRow([ft.DataCell(ft.Text(f"-- {gender.upper()} --", weight="bold", color="blue"))] + [ft.DataCell(ft.Text(""))]*(len(cols)-1)))
                    for r in data[gender]:
                        cells = [ft.DataCell(ft.Text(str(r['rank']))), ft.DataCell(ft.Text(str(r['number']))), ft.DataCell(ft.Text(r['name']))]
                        for s in r['scores']: cells.append(ft.DataCell(ft.Text(str(s))))
                        cells.append(ft.DataCell(ft.Text(str(r['total']), weight="bold", color="green")))
                        rows.append(ft.DataRow(cells))
            
            return ft.DataTable(columns=[ft.DataColumn(ft.Text(c, size=12)) for c in cols], rows=rows, heading_row_height=30, column_spacing=10)

        tabs = [ft.Tab(text="OVERALL", content=ft.Column([build_matrix(None)], scroll="adaptive"))]
        for s in segments:
            tabs.append(ft.Tab(text=s.name.upper(), content=ft.Column([build_matrix(s.id)], scroll="adaptive")))

        scores_tab_content.controls.append(ft.Tabs(tabs=tabs, expand=True))
        page.update()

    # --- MAIN ASSEMBLY ---
    # Trigger initial load for all tabs
    refresh_config_tab()
    refresh_contestant_tab()
    refresh_judges_tab()
    refresh_scores_tab()

    return ft.Container(
        content=ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Configuration", icon=ft.Icons.SETTINGS, content=config_tab_content),
                ft.Tab(text="Contestants", icon=ft.Icons.PEOPLE, content=contestant_tab_content),
                ft.Tab(text="Judges", icon=ft.Icons.GAVEL, content=judges_tab_content),
                ft.Tab(text="Tabulation", icon=ft.Icons.LEADERBOARD, content=scores_tab_content),
            ],
            expand=True
        ),
        padding=10,
        expand=True
    )