import flet as ft
from services.admin_service import AdminService
from services.event_service import EventService
from components.dialogs import show_about_dialog, show_contact_dialog
from views.audit_log_view import AuditLogView

def AdminDashboardView(page: ft.Page, on_logout_callback):
    admin_service = AdminService()
    event_service = EventService()
    current_admin_id = page.session.get("user_id")
    user_role = page.session.get("user_role")

    # --- PERMISSION CHECK ---
    # If AdminViewer, we hide edit/delete actions
    is_read_only = (user_role == "AdminViewer")

    # ---------------------------------------------------------
    # 1. HEADER (Standardized)
    # ---------------------------------------------------------
    header_logo = ft.Container(
        width=40, height=40, border_radius=50, bgcolor="transparent",
        border=ft.border.all(2, "black"), padding=5,
        content=ft.Image(src="hammer.png", fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.GAVEL, color="black"))
    )

    header = ft.Container(
        height=70, padding=ft.padding.symmetric(horizontal=20), bgcolor="#80C1FF",
        shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.GREY_300),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(spacing=10, controls=[
                    header_logo, 
                    # Update Title to reflect role if Viewer
                    ft.Text("JUDGEMENOT" if not is_read_only else "JUDGEMENOT (Auditor)", size=20, weight="bold", color="black")
                ]),
                ft.Row(spacing=5, controls=[
                    ft.TextButton("LEADERBOARD", icon=ft.Icons.EMOJI_EVENTS, style=ft.ButtonStyle(color="black"), on_click=lambda e: page.go("/leaderboard")),
                    ft.TextButton("ABOUT", style=ft.ButtonStyle(color="black"), on_click=lambda e: show_about_dialog(page)),
                    ft.TextButton("CONTACT", style=ft.ButtonStyle(color="black"), on_click=lambda e: show_contact_dialog(page)),
                    ft.VerticalDivider(width=10, color="transparent"),
                    ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="red", tooltip="Log Out", on_click=on_logout_callback)
                ])
            ]
        )
    )

    # Main Scrollable Area
    main_content_area = ft.Column(expand=True, scroll="adaptive")

    # ---------------------------------------------------------
    # 3. GLOBAL DIALOGS
    # ---------------------------------------------------------
    
    # --- ADD USER ---
    new_user_name = ft.TextField(label="Full Name", dense=True)
    new_user_user = ft.TextField(label="Username", dense=True)
    new_user_pass = ft.TextField(label="Password", password=True, can_reveal_password=True, dense=True)
    new_user_role = ft.Dropdown(label="Role", dense=True, options=[
        ft.dropdown.Option("Judge"), ft.dropdown.Option("Tabulator"), 
        ft.dropdown.Option("AdminViewer"), ft.dropdown.Option("Admin")
    ])

    def save_user(e):
        if not new_user_user.value or not new_user_pass.value:
            page.open(ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED)); return
        success, msg = admin_service.create_user(current_admin_id, new_user_name.value, new_user_user.value, new_user_pass.value, new_user_role.value)
        if success: 
            page.open(ft.SnackBar(ft.Text("User Added!"), bgcolor=ft.Colors.GREEN)); page.close(user_dialog); load_users_view()
        else: 
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))
    
    user_dialog = ft.AlertDialog(title=ft.Text("Add New User"), content=ft.Column([new_user_name, new_user_user, new_user_pass, new_user_role], height=250, width=400, tight=True), actions=[ft.TextButton("Save", on_click=save_user)])
    def open_add_user_dialog(e): new_user_name.value = ""; new_user_user.value = ""; new_user_pass.value = ""; page.open(user_dialog)

    # --- ADD EVENT ---
    new_event_name = ft.TextField(label="Event Name", dense=True)
    new_event_type = ft.Dropdown(label="Event Type", dense=True, options=[ft.dropdown.Option("Pageant"), ft.dropdown.Option("QuizBee")], value="Pageant")
    
    def save_event(e):
        if not new_event_name.value or not new_event_type.value: 
            page.open(ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED)); return
        success, msg = admin_service.create_event(current_admin_id, new_event_name.value, new_event_type.value)
        if success: 
            page.open(ft.SnackBar(ft.Text("Event Created!"), bgcolor=ft.Colors.GREEN)); page.close(event_dialog); load_events_view() 
        else: 
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))
            
    event_dialog = ft.AlertDialog(title=ft.Text("Create New Event"), content=ft.Column([new_event_name, new_event_type], height=150, width=400), actions=[ft.TextButton("Create", on_click=save_event)])
    def open_add_event_dialog(e): new_event_name.value = ""; page.open(event_dialog)

    # ---------------------------------------------------------
    # 4. SUB-VIEWS
    # ---------------------------------------------------------

    # --- USERS VIEW ---
    def load_users_view():
        users = admin_service.get_all_users()
        
        # Edit Dialog Logic
        edit_id_tracker = ft.Text(visible=False)
        edit_name = ft.TextField(label="Full Name", dense=True)
        edit_user = ft.TextField(label="Username", dense=True)
        edit_pass = ft.TextField(label="New Password (leave empty to keep)", password=True, can_reveal_password=True, dense=True)
        edit_role = ft.Dropdown(label="Role", dense=True, options=[
            ft.dropdown.Option("Judge"), ft.dropdown.Option("Tabulator"), 
            ft.dropdown.Option("AdminViewer"), ft.dropdown.Option("Admin")
        ])
        edit_is_active_toggle = ft.Switch(label="Account Active & Approved", active_color="green")

        def save_edit_user(e):
            if not edit_id_tracker.value: return
            final_is_pending = False
            final_is_active = edit_is_active_toggle.value
            success, msg = admin_service.update_user(current_admin_id, int(edit_id_tracker.value), edit_name.value, edit_user.value, edit_role.value, edit_pass.value if edit_pass.value else None, final_is_pending, final_is_active)
            if success: page.open(ft.SnackBar(ft.Text("Updated!"), bgcolor="green")); page.close(edit_dialog); load_users_view()
            else: page.open(ft.SnackBar(ft.Text(f"Failed: {msg}"), bgcolor="red"))

        edit_dialog = ft.AlertDialog(title=ft.Text("Edit User"), content=ft.Column([edit_name, edit_user, edit_role, edit_is_active_toggle, edit_pass], height=350, width=400, tight=True), actions=[ft.TextButton("Cancel", on_click=lambda _: page.close(edit_dialog)), ft.ElevatedButton("Update", on_click=save_edit_user)])

        def open_edit_dialog(e):
            u_id = e.control.data
            target = next((u for u in users if u.id == u_id), None)
            if target:
                edit_id_tracker.value = str(target.id)
                edit_name.value = target.name
                edit_user.value = target.username
                edit_role.value = target.role
                edit_is_active_toggle.value = (target.is_active and not target.is_pending)
                edit_pass.value = ""
                page.open(edit_dialog)

        def delete_user_click(e):
            uid = e.control.data
            def confirm(ev): 
                admin_service.delete_user(current_admin_id, uid); page.close(del_dlg); load_users_view()
            del_dlg = ft.AlertDialog(title=ft.Text("Confirm Delete"), content=ft.Text("Irreversible action."), actions=[ft.TextButton("Cancel", on_click=lambda _: page.close(del_dlg)), ft.TextButton("Delete", on_click=confirm, style=ft.ButtonStyle(color="red"))])
            page.open(del_dlg)

        # Build Data Table
        rows = []
        for u in users:
            status_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color="green") if u.is_active and not u.is_pending else ft.Icon(ft.Icons.WARNING, color="orange")
            
            # ACTIONS COLUMN: Visible only if NOT Read Only
            actions_content = ft.Row([
                ft.IconButton(ft.Icons.EDIT, icon_color="blue", data=u.id, on_click=open_edit_dialog),
                ft.IconButton(ft.Icons.DELETE, icon_color="red", data=u.id, on_click=delete_user_click)
            ]) if not is_read_only else ft.Text("View Only", color="grey", italic=True)

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(u.id))),
                ft.DataCell(ft.Row([status_icon, ft.Text(u.name)], spacing=10)),
                ft.DataCell(ft.Text(u.role)),
                ft.DataCell(ft.Text(u.username)),
                ft.DataCell(actions_content)
            ]))

        content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: load_welcome_view()),
                    ft.Text("User Management", size=24, weight="bold"),
                    ft.Container(expand=True),
                    # Hide Add button if read only
                    ft.ElevatedButton("Add User", icon=ft.Icons.ADD, on_click=open_add_user_dialog, bgcolor="#64AEFF", color="white", visible=not is_read_only)
                ]),
                ft.Divider(),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("ID")),
                        ft.DataColumn(ft.Text("Name")),
                        ft.DataColumn(ft.Text("Role")),
                        ft.DataColumn(ft.Text("Username")),
                        ft.DataColumn(ft.Text("Actions")),
                    ],
                    rows=rows,
                    heading_row_color="#F0F8FF",
                    border=ft.border.all(1, "#E0E0E0"),
                    border_radius=10,
                    width=float("inf")
                )
            ]),
            padding=30,
            bgcolor="white",
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12),
            margin=20
        )
        main_content_area.controls = [content]
        page.update()

    # --- EVENTS VIEW ---
    def load_events_view():
        events = admin_service.get_all_events()
        
        # FIXED: Correctly defined and implemented with feedback
        def toggle_event_status(e, status):
            # Check if e is just an ID (when called directly) or a control event
            event_id = e if isinstance(e, int) else e.control.data
            
            success, msg = event_service.update_event_status(current_admin_id, event_id, status)
            if success:
                page.open(ft.SnackBar(ft.Text(msg), bgcolor="green"))
                load_events_view()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        
        # --- NEW: DELETE EVENT HANDLER ---
        def delete_event_click(e):
            ev_id = e.control.data
            def confirm_del(ev):
                success, msg = admin_service.delete_event(current_admin_id, ev_id)
                page.close(del_evt_dlg)
                if success:
                    page.open(ft.SnackBar(ft.Text(msg), bgcolor="green"))
                    load_events_view()
                else:
                    page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))

            del_evt_dlg = ft.AlertDialog(
                title=ft.Text("Delete Event?"), 
                content=ft.Text("WARNING: This will delete ALL scores, segments, and data for this event. Irreversible."), 
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _: page.close(del_evt_dlg)), 
                    ft.ElevatedButton("Delete Forever", on_click=confirm_del, bgcolor="red", color="white")
                ]
            )
            page.open(del_evt_dlg)

        cards = []
        for e in events:
            is_active = e.status == "Active"
            status_color = "green" if is_active else "grey"
            icon = ft.Icons.WOMAN if e.event_type == "Pageant" else ft.Icons.LIGHTBULB
            
            bg_image = "pageant.png" if e.event_type == "Pageant" else "quiz.png"
            
            # ACTION ROW: Hide status controls if read only
            if not is_read_only:
                # If active, button stops it. If ended/inactive, button starts it.
                if e.status == "Active":
                    action_icon = ft.IconButton(icon=ft.Icons.STOP_CIRCLE, icon_color="red", tooltip="End Event", data=e.id, on_click=lambda x: toggle_event_status(x, "Ended"))
                else:
                    action_icon = ft.IconButton(icon=ft.Icons.PLAY_CIRCLE_FILL, icon_color="green", tooltip="Activate Event", data=e.id, on_click=lambda x: toggle_event_status(x, "Active"))
                
                # Popup menu now includes DELETE
                popup_menu = ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(text="Activate", on_click=lambda x, eid=e.id: toggle_event_status(eid, "Active")),
                        ft.PopupMenuItem(text="End Event", on_click=lambda x, eid=e.id: toggle_event_status(eid, "Ended")),
                        ft.PopupMenuItem(text="Delete Event", icon=ft.Icons.DELETE, on_click=delete_event_click, data=e.id),
                    ]
                )
            else:
                action_icon = ft.Container() # Empty
                popup_menu = ft.Container() # Empty

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(content=ft.Icon(icon, color="white"), padding=10, bgcolor="#64AEFF", border_radius=10),
                        ft.Column([
                            ft.Text(e.name, weight="bold", size=16, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{e.event_type} • {e.status}", color=status_color, size=12)
                        ], spacing=2, expand=True),
                        popup_menu
                    ], alignment=ft.MainAxisAlignment.START),
                    
                    # SPACER forces the button to the bottom
                    ft.Container(expand=True),
                    
                    ft.Row([
                        ft.ElevatedButton("Manage", expand=True, bgcolor="#E3F2FD", color="#1565C0", data=e.id, on_click=lambda x: page.go(f"/admin/event/{x.control.data}")),
                        action_icon
                    ], alignment="spaceBetween")
                ]),
                padding=20,
                width=300, 
                height=220, # Fixed height ensures uniform grid and working Spacer
                bgcolor="white",
                # BACKGROUND IMAGE with opacity
                image=ft.DecorationImage(src=bg_image, fit=ft.ImageFit.COVER, opacity=0.15), 
                border_radius=15,
                shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.BLACK12),
                border=ft.border.all(1, "#E0E0E0")
            )
            cards.append(card)

        content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: load_welcome_view()),
                    ft.Text("Event Management", size=24, weight="bold"),
                    ft.Container(expand=True),
                    # Hide Create button if read only
                    ft.ElevatedButton("Create Event", icon=ft.Icons.ADD, on_click=open_add_event_dialog, bgcolor="#64AEFF", color="white", visible=not is_read_only)
                ]),
                ft.Divider(),
                ft.GridView(runs_count=3, max_extent=350, spacing=20, run_spacing=20, controls=cards)
            ]),
            padding=30,
            bgcolor="white",
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12),
            margin=20,
            expand=True
        )
        main_content_area.controls = [content]
        page.update()

    def load_audit_logs():
        # Wrapper to style the Audit Log view consistently
        content = ft.Container(
            content=AuditLogView(page, on_back_click=lambda e: load_welcome_view()),
            padding=0,
            bgcolor="white",
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12),
            margin=20,
            expand=True,
            # FIXED: Removed explicit height=600 so it can fill the screen
        )
        main_content_area.controls = [content]
        page.update()

    # --- HOME VIEW ---
    def load_welcome_view():
        # Stats Fetching
        users_count = len(admin_service.get_all_users())
        events_count = len(admin_service.get_all_events())
        
        def stat_card(title, value, icon, color):
            return ft.Container(
                content=ft.Row([
                    ft.Container(content=ft.Icon(icon, color="white", size=30), padding=15, bgcolor=color, border_radius=10),
                    ft.Column([
                        ft.Text(title, color="grey", size=12),
                        ft.Text(str(value), weight="bold", size=24)
                    ], spacing=0)
                ], alignment="start"),
                padding=20,
                bgcolor="white",
                border_radius=15,
                shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12),
                width=250
            )

        def menu_card(title, desc, icon, color, on_click):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, size=40, color=color),
                    ft.Text(title, weight="bold", size=16),
                    ft.Text(desc, size=12, color="grey", text_align="center")
                ], horizontal_alignment="center", alignment="center"),
                padding=30,
                bgcolor="white",
                border_radius=15,
                shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12),
                border=ft.border.all(1, "transparent"),
                width=280,
                height=200,
                ink=True,
                on_click=on_click,
                animate=ft.Animation(200, "easeOut"),
                on_hover=lambda e: (
                    setattr(e.control, 'border', ft.border.all(2, color) if e.data == "true" else ft.border.all(1, "transparent")),
                    e.control.update()
                )
            )
        
        # Display simplified text if Read Only
        welcome_msg = f"Welcome back, Admin." if not is_read_only else f"Welcome, Auditor. System in Read-Only Mode."

        content = ft.Column([
            ft.Text("Dashboard Overview", size=28, weight="bold"),
            ft.Text(welcome_msg, color="grey"),
            ft.Container(height=20),
            
            # 1. Stats Row
            ft.Row([
                stat_card("Total Users", users_count, ft.Icons.PEOPLE, "#64AEFF"),
                stat_card("Total Events", events_count, ft.Icons.EVENT, "#FFB74D"),
                stat_card("System Status", "Online", ft.Icons.CHECK_CIRCLE, "#81C784"),
            ], wrap=True, spacing=20),
            
            ft.Container(height=40),
            ft.Text("Quick Actions", size=20, weight="bold"),
            ft.Container(height=10),
            
            # 2. Navigation Cards
            ft.Row([
                menu_card("User Management", "View active judges and staff.", ft.Icons.MANAGE_ACCOUNTS, "#64AEFF", lambda e: load_users_view()),
                menu_card("Event Management", "Monitor pageants and quizzes.", ft.Icons.EVENT_NOTE, "#FFB74D", lambda e: load_events_view()),
                menu_card("Security Audit", "View system logs and activity trails.", ft.Icons.SECURITY, "#E57373", lambda e: load_audit_logs()),
            ], wrap=True, spacing=30, alignment="start")
        ], scroll="adaptive")

        main_content_area.controls = [ft.Container(content, padding=40)]
        page.update()

    # Initial Load
    load_welcome_view()

    return ft.Column(
        expand=True,
        controls=[
            header,
            ft.Container(
                content=main_content_area,
                expand=True,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#DDF4FF", "#FDE9FF"]
                )
            )
        ],
        spacing=0
    )