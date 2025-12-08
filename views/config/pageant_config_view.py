import flet as ft
from services.pageant_service import PageantService
from services.event_service import EventService
from core.database import SessionLocal
from models.all_models import Segment, Criteria

def PageantConfigView(page: ft.Page, event_id: int):
    # Services
    pageant_service = PageantService()
    event_service = EventService()

    # State
    editing_segment_id = None 
    editing_criteria_id = None 
    selected_segment_id = None
    pending_action_seg_id = None 

    # --- UI CONTROLS ---
    p_seg_name = ft.TextField(label="Segment Name", width=280)
    p_seg_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    p_crit_name = ft.TextField(label="Criteria Name", width=280)
    p_crit_weight = ft.TextField(label="Weight (%)", suffix_text="%", keyboard_type=ft.KeyboardType.NUMBER, width=280)
    p_is_final = ft.Checkbox(label="Is Final Round?", value=False)
    p_qualifiers = ft.TextField(label="Qualifiers Count", value="5", width=280, visible=False, keyboard_type=ft.KeyboardType.NUMBER)
    
    # Main Container for this View
    main_column = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def on_final_check(e):
        p_qualifiers.visible = p_is_final.value
        p_seg_weight.disabled = p_is_final.value 
        if p_is_final.value: p_seg_weight.value = "100" 
        page.update()
    p_is_final.on_change = on_final_check

    # --- REFRESH LOGIC (Internal to this view) ---
    def refresh_view():
        main_column.controls.clear()
        
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).all()
        final_round_is_active = any(s.is_active and s.is_final for s in segments)

        main_column.controls.append(ft.Row([
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
                                    # Fix Loop Variable Capture
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
            main_column.controls.append(card)
        
        if current_total_weight > 1.0001:
            main_column.controls.append(ft.Text(f"⚠️ Prelim Weight is {int(current_total_weight*100)}%. It should be 100%.", color="red"))
        elif current_total_weight < 0.999:
            main_column.controls.append(ft.Text(f"ℹ️ Prelim Weight is {int(current_total_weight*100)}%. Add more segments.", color="blue"))
        else:
             main_column.controls.append(ft.Text("✅ Prelim Weight is 100%.", color="green"))

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
            refresh_view()
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
            refresh_view()
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
                refresh_view()
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
                refresh_view()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
             page.open(ft.SnackBar(ft.Text("Invalid Weight"), bgcolor="red"))

    # Dialogs
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

    # Initial Render
    refresh_view()
    
    return ft.Container(content=main_column, padding=20)