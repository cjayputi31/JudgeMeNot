import flet as ft
from services.admin_service import AdminService
from services.event_service import EventService
# IMPORT SHARED DIALOGS
from components.dialogs import show_about_dialog, show_contact_dialog
# IMPORT AUDIT LOG VIEW (Ensures IAS Security Requirement is visible)
from views.audit_log_view import AuditLogView

def AdminDashboardView(page: ft.Page, on_logout_callback):
    admin_service = AdminService()
    event_service = EventService()
    page.assets_dir = "assets"
    
    # GET CURRENT ADMIN ID FOR LOGGING
    current_admin_id = page.session.get("user_id")

    # ---------------------------------------------------------
    # 0. LOGOUT LOGIC
    # ---------------------------------------------------------
    def confirm_logout(e):
        # The route change in main.py will automatically clear this dialog.
        on_logout_callback(e)

    logout_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirm Logout"),
        content=ft.Text("Are you sure you want to log out?"),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(logout_dialog)),
            ft.ElevatedButton("Log Out", bgcolor=ft.Colors.RED, color=ft.Colors.WHITE, on_click=confirm_logout)
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # ---------------------------------------------------------
    # 1. HEADER
    # ---------------------------------------------------------
    HEADER_COLOR = "#80C1FF"

    # --- HEADER UI ---
    header_logo = ft.Container(
        width=45, height=45, border_radius=50, bgcolor="transparent",
        border=ft.border.all(2, ft.Colors.BLACK), padding=5,
        content=ft.Image(src="hammer.png", fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.GAVEL))
    )

    header = ft.Container(
        height=75, padding=ft.padding.symmetric(horizontal=50), bgcolor=HEADER_COLOR,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(spacing=10, controls=[header_logo, ft.Text("JUDGEMENOT", size=22, weight="bold", color=ft.Colors.BLACK)]),

                # NAVIGATION & LOGOUT
                ft.Row(spacing=10, controls=[
                    # Use shared functions
                    ft.TextButton("ABOUT", style=ft.ButtonStyle(color=ft.Colors.BLACK), on_click=lambda e: show_about_dialog(page)),
                    ft.TextButton("CONTACT", style=ft.ButtonStyle(color=ft.Colors.BLACK), on_click=lambda e: show_contact_dialog(page)),
                    ft.VerticalDivider(width=10, color="transparent"),
                    ft.IconButton(
                        icon=ft.Icons.LOGOUT, 
                        icon_color=ft.Colors.RED_700, 
                        tooltip="Log Out",
                        on_click=on_logout_callback # DIRECT CALL (No Dialog)
                    )
                ])
            ]
        )
    )

    # ---------------------------------------------------------
    # 2. MAIN CONTENT AREA
    # ---------------------------------------------------------
    # This container changes based on what menu item is clicked
    main_content_area = ft.Container(expand=True, padding=40)

    # ---------------------------------------------------------
    # 3. GLOBAL DIALOGS (User & Event Creation)
    # ---------------------------------------------------------

    # --- ADD USER DIALOG ---
    new_user_name = ft.TextField(label="Full Name")
    new_user_user = ft.TextField(label="Username")
    new_user_pass = ft.TextField(label="Password", password=True, can_reveal_password=True)
    new_user_role = ft.Dropdown(label="Role", options=[
        ft.dropdown.Option("Judge"), 
        ft.dropdown.Option("Tabulator"), 
        ft.dropdown.Option("AdminViewer"), 
        ft.dropdown.Option("Admin")
    ])

    def save_user(e):
        if not new_user_user.value or not new_user_pass.value:
            page.open(ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED))
            return
        
        # PASS ADMIN ID FOR LOGGING
        success, msg = admin_service.create_user(
            current_admin_id,
            new_user_name.value, 
            new_user_user.value, 
            new_user_pass.value, 
            new_user_role.value
        )
        
        if success: 
            page.open(ft.SnackBar(ft.Text("User Added!"), bgcolor=ft.Colors.GREEN))
            page.close(user_dialog)
            load_users_view() # Refresh if currently on users view
        else: 
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))

    user_dialog = ft.AlertDialog(
        title=ft.Text("Add New User"), 
        content=ft.Column([new_user_name, new_user_user, new_user_pass, new_user_role], height=300, width=400), 
        actions=[ft.TextButton("Save", on_click=save_user)]
    )

    def open_add_user_dialog(e): 
        # Reset fields
        new_user_name.value = ""
        new_user_user.value = ""
        new_user_pass.value = ""
        page.open(user_dialog)

    # --- ADD EVENT DIALOG ---
    new_event_name = ft.TextField(label="Event Name")
    new_event_type = ft.Dropdown(label="Event Type", options=[ft.dropdown.Option("Pageant"), ft.dropdown.Option("QuizBee")], value="Pageant")

    def save_event(e):
        if not new_event_name.value or not new_event_type.value: 
            page.open(ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED))
            return
        
        # PASS ADMIN ID FOR LOGGING
        success, msg = admin_service.create_event(current_admin_id, new_event_name.value, new_event_type.value)
        
        if success: 
            page.open(ft.SnackBar(ft.Text("Event Created!"), bgcolor=ft.Colors.GREEN))
            page.close(event_dialog)
            load_events_view() 
        else: 
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))

    event_dialog = ft.AlertDialog(
        title=ft.Text("Create New Event"), 
        content=ft.Column([new_event_name, new_event_type], height=150, width=400), 
        actions=[ft.TextButton("Create", on_click=save_event)]
    )

    def open_add_event_dialog(e): 
        new_event_name.value = ""
        page.open(event_dialog)

    # ---------------------------------------------------------
    # 4. VIEWS (Sub-pages)
    # ---------------------------------------------------------

    # --- USERS VIEW ---
    def load_users_view():
        users = admin_service.get_all_users()

        # --- DELETE LOGIC ---
        def open_delete_dialog(e):
            user_id = e.control.data
            def confirm_delete(ev):
                try:
                    # PASS ADMIN ID FOR LOGGING
                    success, msg = admin_service.delete_user(current_admin_id, user_id)
                    color = ft.Colors.GREEN if success else ft.Colors.RED
                    page.open(ft.SnackBar(ft.Text(msg), bgcolor=color))
                    
                    page.close(delete_dialog)
                    load_users_view()
                except Exception as ex:
                    page.open(ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor=ft.Colors.RED))

            delete_dialog = ft.AlertDialog(
                title=ft.Text("Delete User?"), 
                content=ft.Text("This action cannot be undone."), 
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _: page.close(delete_dialog)), 
                    ft.TextButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(color="red"))
                ]
            )
            page.open(delete_dialog)

        # --- EDIT LOGIC (COMPLETED) ---
        edit_id_tracker = ft.Text(visible=False)
        edit_name = ft.TextField(label="Full Name")
        edit_user = ft.TextField(label="Username")
        edit_pass = ft.TextField(label="New Password (leave empty to keep)", password=True, can_reveal_password=True)
        edit_role = ft.Dropdown(label="Role", options=[
            ft.dropdown.Option("Judge"), ft.dropdown.Option("Tabulator"), 
            ft.dropdown.Option("AdminViewer"), ft.dropdown.Option("Admin")
        ])

        def save_edit_user(e):
            # PASS ADMIN ID FOR LOGGING
            success, msg = admin_service.update_user(
                current_admin_id,
                edit_id_tracker.value, 
                edit_name.value, 
                edit_user.value, 
                edit_role.value, 
                edit_pass.value if edit_pass.value else None
            )
            if success:
                page.open(ft.SnackBar(ft.Text("User Updated Successfully!"), bgcolor=ft.Colors.GREEN))
                page.close(edit_dialog)
                load_users_view()
            else:
                page.open(ft.SnackBar(ft.Text(f"Update Failed: {msg}"), bgcolor=ft.Colors.RED))

        edit_dialog = ft.AlertDialog(
            title=ft.Text("Edit User Details"),
            content=ft.Column([edit_name, edit_user, edit_role, edit_pass], height=300, width=400),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.close(edit_dialog)),
                ft.ElevatedButton("Update", on_click=save_edit_user)
            ]
        )

        def open_edit_dialog(e):
            user_id = e.control.data
            target_user = next((u for u in users if u.id == user_id), None)
            if target_user:
                edit_id_tracker.value = target_user.id
                edit_name.value = target_user.name
                edit_user.value = target_user.username
                edit_role.value = target_user.role
                edit_pass.value = "" # Reset password field
                page.open(edit_dialog)

        # --- TABLE CONSTRUCTION ---
        TABLE_WIDTH = 900
        table_rows = []
        for u in users:
            action_btn = ft.TextButton("Edit", data=u.id, icon=ft.Icons.EDIT, style=ft.ButtonStyle(color=ft.Colors.BLUE), on_click=open_edit_dialog)
            delete_icon = ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, data=u.id, on_click=open_delete_dialog)

            row = ft.Container(
                width=TABLE_WIDTH, bgcolor=ft.Colors.WHITE, border_radius=8, padding=10, margin=ft.margin.only(bottom=8), 
                shadow=ft.BoxShadow(blur_radius=2, color=ft.Colors.GREY_300), 
                content=ft.Row([
                    ft.Container(ft.Text(str(u.id)), width=50), 
                    ft.Container(ft.Text(u.name), width=200), 
                    ft.Container(ft.Text(u.role, weight="bold", color="blue" if u.role=="Admin" else "black"), width=150), 
                    ft.Container(ft.Text(u.username), width=150), 
                    ft.Container(ft.Row([action_btn, delete_icon], spacing=0), width=180)
                ])
            )
            table_rows.append(row)

        table_header = ft.Container(
            width=TABLE_WIDTH, bgcolor=ft.Colors.BLUE_100, padding=10, border_radius=8, 
            content=ft.Row([
                ft.Container(ft.Text("ID", weight="bold"), width=50), 
                ft.Container(ft.Text("Name", weight="bold"), width=200), 
                ft.Container(ft.Text("Role", weight="bold"), width=150), 
                ft.Container(ft.Text("Username", weight="bold"), width=150), 
                ft.Container(ft.Text("Actions", weight="bold"), width=180)
            ])
        )

        main_content_area.content = ft.Column([
            # BACK BUTTON + HEADER
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=30, on_click=lambda e: load_welcome_view()),
                ft.Text("Manage Users", size=24, weight="bold")
            ]),
            ft.ElevatedButton("Add New User", icon=ft.Icons.ADD, on_click=open_add_user_dialog),
            ft.Divider(),
            ft.Row([table_header], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.Column(table_rows, scroll="adaptive", expand=True)], alignment=ft.MainAxisAlignment.CENTER, expand=True),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
        page.update()

    # --- EVENTS VIEW ---
    def load_events_view():
        events = admin_service.get_all_events()
        events_list = ft.Column(spacing=10, scroll="adaptive", expand=True)

        def toggle_event_status(e, new_status):
            event_id = e.control.data
            # PASS ADMIN ID FOR LOGGING
            success, msg = event_service.update_event_status(current_admin_id, event_id, new_status)
            if success: 
                page.open(ft.SnackBar(ft.Text(f"Event is now {new_status}!"), bgcolor=ft.Colors.GREEN))
                load_events_view()
            else: 
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))

        for e in events:
            bg_img = "pageant.png" if e.event_type == "Pageant" else "quiz.png"
            icon = ft.Icons.WOMAN if e.event_type == "Pageant" else ft.Icons.LIGHTBULB
            col = ft.Colors.WHITE

            # Action Button Logic
            if e.status == "Active":
                action_icon = ft.IconButton(icon=ft.Icons.STOP_CIRCLE, icon_color="red", tooltip="End Event", data=e.id, on_click=lambda x: toggle_event_status(x, "Ended"))
                status_color = ft.Colors.GREEN_400
            else:
                action_icon = ft.IconButton(icon=ft.Icons.PLAY_CIRCLE_FILL, icon_color="green", tooltip="Activate Event", data=e.id, on_click=lambda x: toggle_event_status(x, "Active"))
                status_color = ft.Colors.GREY_400

            card_content = ft.Container(
                padding=20, bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.BLACK),
                content=ft.Row([
                    ft.Row([
                        ft.Icon(icon, color=col, size=30), 
                        ft.Column([
                            ft.Text(e.name, size=20, weight="bold", color=col), 
                            ft.Row([
                                ft.Text(f"{e.event_type} • ", color=ft.Colors.GREY_400), 
                                ft.Text(e.status, color=status_color, weight="bold")
                            ], spacing=2)
                        ], spacing=2)
                    ], expand=True),

                    ft.Row([
                        ft.ElevatedButton("Manage", data=e.id, on_click=lambda ev: page.go(f"/admin/event/{ev.control.data}")),
                        action_icon
                    ], spacing=10)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )

            # Use Image as background decoration
            events_list.controls.append(
                ft.Container(
                    height=100, border_radius=10, 
                    image=ft.DecorationImage(src=bg_img, fit=ft.ImageFit.COVER, opacity=0.8), 
                    padding=0, clip_behavior=ft.ClipBehavior.HARD_EDGE, 
                    content=card_content,
                    shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.GREY_400)
                )
            )

        main_content_area.content = ft.Column([
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=30, on_click=lambda e: load_welcome_view()),
                ft.Text("Manage Events", size=24, weight="bold")
            ]),
            ft.ElevatedButton("Create Event", icon=ft.Icons.ADD, on_click=open_add_event_dialog),
            ft.Divider(),
            ft.Container(content=events_list, expand=True)
        ], expand=True)
        page.update()

    # --- AUDIT LOGS VIEW (Sub-function wrapper) ---
    def load_audit_logs():
        # Pass the callback to go back to the welcome screen
        content = AuditLogView(page, on_back_click=lambda e: load_welcome_view())
        main_content_area.content = content
        page.update()

    # --- DASHBOARD (WELCOME) VIEW ---
    def load_welcome_view():
        def nav_card(title, icon, desc, color, on_click):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, size=40, color="white"),
                    ft.Text(title, size=20, weight="bold", color="white"),
                    ft.Text(desc, color="white70", size=12, text_align="center")
                ], alignment="center", horizontal_alignment="center"),
                width=250, height=150, bgcolor=color, border_radius=15,
                padding=20, ink=True, on_click=on_click,
                shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.GREY_400),
                animate=ft.Animation(300, "easeOut")
            )

        content = ft.Column([
            ft.Text("Admin Dashboard", size=32, weight="bold"),
            ft.Text("Welcome back, Admin.", size=16, color="grey"),
            ft.Divider(height=30),

            # Quick Stats
            ft.Container(
                padding=20, bgcolor=ft.Colors.BLUE_50, border_radius=10, width=float("inf"), 
                content=ft.Column([
                    ft.Text("System Status", weight="bold", size=16, color=ft.Colors.BLUE_900), 
                    ft.Row([
                        ft.Column([ft.Text("Server"), ft.Text("Online", color="green", weight="bold")]), 
                        ft.VerticalDivider(), 
                        ft.Column([ft.Text("Database"), ft.Text("Connected", color="green", weight="bold")]),
                        ft.VerticalDivider(),
                        ft.Column([ft.Text("Security"), ft.Text("Active", color="green", weight="bold")])
                    ], spacing=50)
                ])
            ),

            ft.Container(height=20),
            ft.Text("Main Menu", size=20, weight="bold"),

            ft.Row([
                nav_card("Manage Users", ft.Icons.PEOPLE, "Add/Edit judges & staff", ft.Colors.BLUE_500, lambda e: load_users_view()),
                nav_card("Manage Events", ft.Icons.EVENT, "Create pageants & quiz bees", ft.Colors.ORANGE_500, lambda e: load_events_view()),
                nav_card("Security Logs", ft.Icons.SECURITY, "View audit trails (IAS)", ft.Colors.RED_500, lambda e: load_audit_logs()),
            ], spacing=20, wrap=True)
        ], scroll="adaptive")

        main_content_area.content = content
        page.update()

    # Initial Load
    load_welcome_view()