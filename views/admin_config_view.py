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

# IMPORT THE NEW SPLIT VIEWS
from views.config.pageant_config_view import PageantConfigView
from views.config.quiz_config_view import QuizConfigView

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
    pending_filename = None

    # NEW: Track if we are editing a contestant
    editing_contestant_id = None 

    # ---------------------------------------------------------
    # 1. FILE PICKER (Shared)
    # ---------------------------------------------------------
    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal uploaded_file_path, pending_filename
        if e.files:
            file_obj = e.files[0]
            if file_obj.path:
                try:
                    os.makedirs("assets/uploads", exist_ok=True)
                    safe_name = "".join(x for x in file_obj.name if x.isalnum() or x in "._-")
                    new_filename = f"img_{int(time.time())}_{safe_name}"
                    dest_path = os.path.join("assets/uploads", new_filename)
                    shutil.copy(file_obj.path, dest_path)
                    uploaded_file_path = f"uploads/{new_filename}"
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
                page.open(ft.SnackBar(ft.Text("Browser Mode detected. Run as Desktop App."), bgcolor="orange"))

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # --- EXPORT PICKER ---
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
                    scope_name = opt.text; break
        safe_name = scope_name.replace(" ", "_")
        ext = "xlsx" if export_format.value == "excel" else "pdf"
        fname = f"{current_event.name}_{safe_name}.{ext}"
        save_file_picker.save_file(dialog_title="Save Score Sheet", file_name=fname)

    export_dialog = ft.AlertDialog(
        title=ft.Text("Export Scores"),
        content=ft.Column([ft.Text("Select Data Source:"), export_scope, ft.Divider(), ft.Text("Select Format:"), export_format], height=200, width=350, tight=True),
        actions=[ft.TextButton("Cancel", on_click=lambda e: page.close(export_dialog)), ft.ElevatedButton("Export", icon=ft.Icons.DOWNLOAD, on_click=initiate_export)]
    )

    def open_export_dialog(e):
        db = SessionLocal()
        segments = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all()
        db.close()
        opts = [ft.dropdown.Option(key="OVERALL", text="Overall Tally")]
        for s in segments: opts.append(ft.dropdown.Option(key=str(s.id), text=s.name))
        export_scope.options = opts
        export_scope.value = "OVERALL"
        page.open(export_dialog)

    def get_event_details():
        db = SessionLocal(); event = db.query(Event).get(event_id); db.close(); return event

    current_event = get_event_details()
    if not current_event: return ft.Container(content=ft.Text("Event not found!"))

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

    def open_add_contestant_dialog(e):
        nonlocal uploaded_file_path, editing_contestant_id
        editing_contestant_id = None # ADD MODE
        
        # Reset Fields
        c_number.value = ""
        c_name.value = ""
        uploaded_file_path = None
        img_preview.visible = False
        img_preview.src = ""
        upload_btn.text = "Upload Photo"
        
        add_c_dialog.title.value = "Add Contestant"
        page.open(add_c_dialog)

    def open_edit_contestant_dialog(e):
        nonlocal uploaded_file_path, editing_contestant_id
        c = e.control.data # Get contestant object passed in data
        editing_contestant_id = c.id # EDIT MODE
        
        # Pre-fill
        c_number.value = str(c.candidate_number)
        c_name.value = c.name
        c_gender.value = c.gender
        
        # Handle Image
        if c.image_path:
            uploaded_file_path = c.image_path # Keep existing unless changed
            img_preview.src = f"{c.image_path}?v={int(time.time())}"
            img_preview.visible = True
            upload_btn.text = "Change Photo"
        else:
            uploaded_file_path = None
            img_preview.visible = False
            upload_btn.text = "Upload Photo"

        add_c_dialog.title.value = "Edit Contestant"
        page.open(add_c_dialog)

    def save_contestant(e):
        if not c_number.value or not c_name.value:
            page.open(ft.SnackBar(ft.Text("Fill Number and Name"), bgcolor="red"))
            return
        try:
            num = int(c_number.value)
            
            if editing_contestant_id:
                # UPDATE
                success, msg = contestant_service.update_contestant(
                    editing_contestant_id, num, c_name.value, c_gender.value, uploaded_file_path
                )
            else:
                # ADD
                success, msg = contestant_service.add_contestant(
                    event_id, num, c_name.value, c_gender.value, uploaded_file_path
                )

            if success:
                page.open(ft.SnackBar(ft.Text(msg), bgcolor="green"))
                page.close(add_c_dialog)
                refresh_ui()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except ValueError:
            page.open(ft.SnackBar(ft.Text("Number must be an integer"), bgcolor="red"))

    add_c_dialog = ft.AlertDialog(
        title=ft.Text("Contestant"),
        content=ft.Column([
            ft.Row([c_number, c_gender]),
            c_name,
            ft.Row([upload_btn, img_preview], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], height=250, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=save_contestant)]
    )

    def delete_contestant_click(e):
        success, msg = contestant_service.delete_contestant(e.control.data)
        if success:
            page.open(ft.SnackBar(ft.Text("Deleted & Reordered"), bgcolor="grey"))
            refresh_ui()
        else:
             page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

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
                        # FIX: Always show ICON for Admin List (No Image Rendering)
                        ft.Container(
                            width=40, height=40, border_radius=20,
                            content=ft.Icon(icon, color="white"),
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
                    ft.Row([
                        # EDIT BUTTON
                        ft.IconButton(icon=ft.Icons.EDIT, icon_color="blue", tooltip="Edit", data=c, on_click=open_edit_contestant_dialog),
                        # DELETE BUTTON
                        ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", tooltip="Delete", data=c.id, on_click=delete_contestant_click)
                    ])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

        col_male = ft.Column(expand=True, scroll="hidden", spacing=10, controls=[ft.Container(content=ft.Text("MALE CANDIDATES", weight="bold", color="blue"), padding=10)] + [create_list_tile(c, ft.Colors.BLUE_50, ft.Icons.MAN) for c in males])
        col_female = ft.Column(expand=True, scroll="hidden", spacing=10, controls=[ft.Container(content=ft.Text("FEMALE CANDIDATES", weight="bold", color="pink"), padding=10)] + [create_list_tile(c, ft.Colors.PINK_50, ft.Icons.WOMAN) for c in females])
        
        return ft.Container(
            padding=20,
            content=ft.Column([
                ft.Row([
                    ft.Text("Manage Participants", size=20, weight="bold"),
                    ft.ElevatedButton("Add Candidate", icon=ft.Icons.ADD, on_click=open_add_contestant_dialog)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Row([
                    ft.Container(col_male, expand=True),
                    ft.VerticalDivider(width=1),
                    ft.Container(col_female, expand=True)
                ], expand=True)
            ], expand=True)
        )

    # ---------------------------------------------------------
    # 3. JUDGES TAB (Shared)
    # ---------------------------------------------------------
    j_select = ft.Dropdown(label="Select Judge", width=300); j_is_chairman = ft.Checkbox(label="Is Chairman?", value=False)
    def load_judge_options(): all_judges = admin_service.get_all_judges(); j_select.options = [ft.dropdown.Option(text=j.name, key=str(j.id)) for j in all_judges]
    def add_judge_click(e):
        if not j_select.value: page.open(ft.SnackBar(ft.Text("Please select a judge"), bgcolor="red")); return
        success, msg = event_service.assign_judge(event_id, int(j_select.value), j_is_chairman.value)
        if success: page.open(ft.SnackBar(ft.Text(msg), bgcolor="green")); page.close(assign_judge_dialog); refresh_ui()
        else: page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
    assign_judge_dialog = ft.AlertDialog(title=ft.Text("Assign Judge"), content=ft.Column([j_select, j_is_chairman], height=150, width=300, tight=True), actions=[ft.TextButton("Cancel", on_click=lambda e: page.close(assign_judge_dialog)), ft.TextButton("Assign", on_click=add_judge_click)])
    def open_assign_judge_dialog(e): j_select.value = None; j_is_chairman.value = False; load_judge_options(); page.open(assign_judge_dialog)
    def remove_judge_click(e): success, msg = event_service.remove_judge(e.control.data); page.open(ft.SnackBar(ft.Text("Judge removed"), bgcolor="green")) if success else None; refresh_ui()
    
    def render_judges_tab():
        assigned = event_service.get_assigned_judges(event_id); list_column = ft.Column(spacing=10, scroll="adaptive", expand=True)
        for entry in assigned:
            role_text = "Chairman" if entry.is_chairman else "Judge"; role_color = "orange" if entry.is_chairman else "blue"
            card = ft.Container(padding=10, bgcolor=ft.Colors.GREY_50, border_radius=10, content=ft.Row([ft.Row([ft.Icon(ft.Icons.GAVEL, color=role_color), ft.Text(entry.judge.name, size=16, weight="bold"), ft.Container(content=ft.Text(role_text, color="white", size=10), bgcolor=role_color, padding=5, border_radius=5)]), ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", data=entry.id, on_click=remove_judge_click)], alignment="spaceBetween"))
            list_column.controls.append(card)
        return ft.Container(padding=20, content=ft.Column([ft.Row([ft.Text("Assigned Judges", size=20, weight="bold"), ft.ElevatedButton("Assign Judge", icon=ft.Icons.ADD, on_click=open_assign_judge_dialog)], alignment="spaceBetween"), ft.Divider(), ft.Text("Assigned Panel", size=16, weight="bold"), list_column], expand=True))

    # ---------------------------------------------------------
    # 4. TABULATION TAB (Shared)
    # ---------------------------------------------------------
    def render_scores_tab():
        db = SessionLocal(); segments = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index).all(); db.close()
        def build_segment_table(gender_data, judges, title, color):
            cols = [ft.DataColumn(ft.Text("Rank"), numeric=True), ft.DataColumn(ft.Text("#"), numeric=True), ft.DataColumn(ft.Text("Candidate"))]
            for j_name in judges: cols.append(ft.DataColumn(ft.Text(j_name, size=12, weight="bold"), numeric=True))
            cols.append(ft.DataColumn(ft.Text("Average"), numeric=True))
            rows = []
            for r in gender_data:
                cells = [ft.DataCell(ft.Text(str(r['rank']), weight="bold")), ft.DataCell(ft.Text(str(r['number']))), ft.DataCell(ft.Text(r['name'], weight="bold" if r['rank']<=3 else "normal"))]
                for score in r['scores']: cells.append(ft.DataCell(ft.Text(str(score))))
                cells.append(ft.DataCell(ft.Text(str(r['total']), weight="bold", color="green")))
                rows.append(ft.DataRow(cells=cells))
            return ft.Column([ft.Container(content=ft.Text(title, weight="bold", color="white"), bgcolor=color, padding=10, border_radius=5, alignment=ft.alignment.center), ft.DataTable(columns=cols, rows=rows, column_spacing=20, heading_row_height=40)], expand=True, scroll="adaptive")
        
        def build_overall_table(gender_data, segment_names, title, color):
            cols = [ft.DataColumn(ft.Text("Rank"), numeric=True), ft.DataColumn(ft.Text("#"), numeric=True), ft.DataColumn(ft.Text("Candidate"))]
            for seg_name in segment_names: cols.append(ft.DataColumn(ft.Text(seg_name, size=12, weight="bold"), numeric=True))
            cols.append(ft.DataColumn(ft.Text("Total %"), numeric=True))
            rows = []
            for r in gender_data:
                cells = [ft.DataCell(ft.Text(str(r['rank']), weight="bold")), ft.DataCell(ft.Text(str(r['number']))), ft.DataCell(ft.Text(r['name'], weight="bold" if r['rank']<=3 else "normal"))]
                for score in r['segment_scores']: cells.append(ft.DataCell(ft.Text(str(score))))
                cells.append(ft.DataCell(ft.Text(str(r['total']), weight="bold", color="green")))
                rows.append(ft.DataRow(cells=cells))
            return ft.Column([ft.Container(content=ft.Text(title, weight="bold", color="white"), bgcolor=color, padding=10, border_radius=5, alignment=ft.alignment.center, width=float("inf")), ft.DataTable(columns=cols, rows=rows, column_spacing=20, heading_row_height=40, width=float("inf"))], expand=True, scroll="adaptive")
        
        def get_tab_content(seg_id=None):
            if seg_id is None:
                matrix = pageant_service.get_overall_breakdown(event_id); seg_names = matrix['segments']
                male_table = build_overall_table(matrix['Male'], seg_names, "MALE OVERALL STANDING", ft.Colors.BLUE)
                female_table = build_overall_table(matrix['Female'], seg_names, "FEMALE OVERALL STANDING", ft.Colors.PINK)
                return ft.Container(padding=10, content=ft.Column([male_table, ft.Divider(), female_table], scroll="adaptive", expand=True))
            else:
                matrix = pageant_service.get_segment_tabulation(event_id, seg_id); judges = matrix['judges']
                male_col = build_segment_table(matrix['Male'], judges, "MALE RANKING", ft.Colors.BLUE)
                female_col = build_segment_table(matrix['Female'], judges, "FEMALE RANKING", ft.Colors.PINK)
                return ft.Container(padding=10, content=ft.Row([male_col, ft.VerticalDivider(width=1), female_col], expand=True))

        score_tabs = [ft.Tab(text="OVERALL TALLY", icon=ft.Icons.ASSESSMENT, content=get_tab_content(None))]
        for s in segments: score_tabs.append(ft.Tab(text=s.name.upper(), content=get_tab_content(s.id)))
        
        return ft.Container(padding=0, content=ft.Column([ft.Container(padding=10, content=ft.Row([ft.Text("Live Tabulation Board", size=20, weight="bold"), ft.Row([ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Refresh Rankings", on_click=lambda e: refresh_ui()), ft.ElevatedButton("Export Scores", icon=ft.Icons.DOWNLOAD, on_click=open_export_dialog)])], alignment="spaceBetween")), ft.Tabs(tabs=score_tabs, animation_duration=300, expand=True, scrollable=True)], expand=True))

    # ---------------------------------------------------------
    # 5. MAIN ASSEMBLY
    # ---------------------------------------------------------
    def render_config_tab():
        if current_event.event_type == "Pageant": return PageantConfigView(page, event_id) # Call Split File
        else: return QuizConfigView(page, event_id)

    tabs = ft.Tabs(selected_index=0, animation_duration=300, tabs=[
        ft.Tab(text="Configuration", icon=ft.Icons.SETTINGS, content=render_config_tab()),
        ft.Tab(text="Contestants", icon=ft.Icons.PEOPLE, content=render_contestant_tab()),
        ft.Tab(text="Judges", icon=ft.Icons.GAVEL, content=render_judges_tab()),
        ft.Tab(text="Tabulation", icon=ft.Icons.LEADERBOARD, content=render_scores_tab()), 
    ], expand=True)

    def refresh_ui():
        # Re-assign content to force redraw
        tabs.tabs[0].content = render_config_tab()
        tabs.tabs[1].content = render_contestant_tab()
        tabs.tabs[2].content = render_judges_tab()
        tabs.tabs[3].content = render_scores_tab()
        page.update()

    return ft.Container(content=ft.Column([ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/admin")), ft.Text(f"Event: {current_event.name}", size=24, weight="bold")]), ft.Divider(), tabs], expand=True), padding=20, expand=True)