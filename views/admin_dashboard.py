import flet as ft
from services.admin_service import AdminService

def AdminDashboardView(page: ft.Page, on_logout_callback):
    admin_service = AdminService()

    page.assets_dir = "assets"

    # ---------------------------------------------------------
    # 1. HEADER (Teammate's Design)
    # ---------------------------------------------------------
    HEADER_COLOR = "#80C1FF"

    def about_clicked(e):
        print("ABOUT clicked")

    def contact_clicked(e):
        print("CONTACT clicked")

    header_logo = ft.Container(
        width=45,
        height=45,
        border_radius=50,
        bgcolor="transparent",
        border=ft.border.all(2, ft.Colors.BLACK),
        padding=5,
        content=ft.Image(
            src="hammer.png",
            fit=ft.ImageFit.CONTAIN,
            error_content=ft.Icon(ft.Icons.GAVEL)
        )
    )

    header_left = ft.Row(
        spacing=10,
        controls=[
            header_logo,
            ft.Text("JUDGEMENOT", size=22, weight="bold", color=ft.Colors.BLACK),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    header_right = ft.Row(
        spacing=40,
        controls=[
            ft.TextButton("ABOUT", style=ft.ButtonStyle(color=ft.Colors.BLACK), on_click=about_clicked),
            ft.TextButton("CONTACT", style=ft.ButtonStyle(color=ft.Colors.BLACK), on_click=contact_clicked),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    header = ft.Container(
        height=75,
        padding=ft.padding.symmetric(horizontal=50),
        bgcolor=HEADER_COLOR,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[header_left, header_right],
        )
    )

    # ---------------------------------------------------------
    # SIDEBAR
    # ---------------------------------------------------------

    sidebar_container = ft.Container(
        width=250,
        visible=False,
        bgcolor=HEADER_COLOR,
        border=ft.border.only(right=ft.border.BorderSide(1, ft.Colors.GREY_300))
    )

    main_content_area = ft.Container(expand=True, padding=20)

    def toggle_sidebar(e):
        sidebar_container.visible = not sidebar_container.visible
        page.update()

    def close_sidebar(e):
        sidebar_container.visible = False
        page.update()

    hamburger_btn = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_size=24,
        on_click=toggle_sidebar,
        tooltip="Open Menu"
    )

    # ---------------------------------------------------------
    # DIALOGS for Add User / Add Event
    # ---------------------------------------------------------

    new_user_name = ft.TextField(label="Full Name")
    new_user_user = ft.TextField(label="Username")
    new_user_pass = ft.TextField(label="Password", password=True, can_reveal_password=True)
    new_user_role = ft.Dropdown(
        label="Role",
        options=[
            ft.dropdown.Option("Judge"),
            ft.dropdown.Option("Tabulator"),
            ft.dropdown.Option("AdminViewer"),
            ft.dropdown.Option("Admin"),
        ]
    )

    def save_user(e):
        if not new_user_user.value or not new_user_pass.value:
            page.open(ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED))
            return

        success, msg = admin_service.create_user(
            new_user_name.value, new_user_user.value,
            new_user_pass.value, new_user_role.value
        )
        
        if success:
            page.open(ft.SnackBar(ft.Text("User Added!"), bgcolor=ft.Colors.GREEN))
            page.close(user_dialog)
            load_users_view()
        else:
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))

    user_dialog = ft.AlertDialog(
        title=ft.Text("Add New User"),
        content=ft.Column([new_user_name, new_user_user, new_user_pass, new_user_role], height=300),
        actions=[ft.TextButton("Save", on_click=save_user)]
    )

    def open_add_user_dialog(e):
        page.open(user_dialog)

    # EVENT DIALOG (unchanged)
    new_event_name = ft.TextField(label="Event Name")
    new_event_type = ft.Dropdown(
        label="Event Type",
        options=[ft.dropdown.Option("Pageant"), ft.dropdown.Option("QuizBee")]
    )

    def save_event(e):
        if not new_event_name.value or not new_event_type.value:
            page.open(ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED))
            return

        success, msg = admin_service.create_event(new_event_name.value, new_event_type.value)

        if success:
            page.open(ft.SnackBar(ft.Text("Event Created!"), bgcolor=ft.Colors.GREEN))
            page.close(event_dialog)
            load_events_view()
        else:
            page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))

    event_dialog = ft.AlertDialog(
        title=ft.Text("Create New Event"),
        content=ft.Column([new_event_name, new_event_type], height=150),
        actions=[ft.TextButton("Create", on_click=save_event)]
    )

    def open_add_event_dialog(e):
        page.open(event_dialog)

    # ---------------------------------------------------------
    # 4. UPDATED USERS VIEW (CENTERED + EXACT WIDTH TABLE)
    # ---------------------------------------------------------

    def load_users_view():
        sidebar_container.visible = False
        users = admin_service.get_all_users()

        # -------------------------------------------------
        # DELETE USER DIALOG
        # -------------------------------------------------
        def open_delete_dialog(e):
            user_id = e.control.data

            def confirm_delete(ev):
                success, msg = admin_service.delete_user(user_id)
                if success:
                    page.open(ft.SnackBar(ft.Text("User Deleted!"), bgcolor=ft.Colors.GREEN))
                    page.close(delete_dialog)
                    load_users_view()
                else:
                    page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))

            delete_dialog = ft.AlertDialog(
                title=ft.Text("Delete User?"),
                content=ft.Text("This action cannot be undone."),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _: page.close(delete_dialog)),
                    ft.TextButton("Delete", on_click=confirm_delete),
                ],
            )
            page.open(delete_dialog)

        # -------------------------------------------------
        # EDIT USER DIALOG (unchanged)
        # -------------------------------------------------
        def open_edit_dialog(e):
            user_id = e.control.data
            user = next((u for u in users if u.id == user_id), None)

            if not user:
                page.open(ft.SnackBar(ft.Text("User not found"), bgcolor=ft.Colors.RED))
                return

            edit_name = ft.TextField(label="Full Name", value=user.name)
            edit_user = ft.TextField(label="Username", value=user.username)
            edit_pass = ft.TextField(label="New Password", password=True, can_reveal_password=True)
            edit_role = ft.Dropdown(
                label="Role",
                value=user.role,
                options=[
                    ft.dropdown.Option("Judge"),
                    ft.dropdown.Option("Tabulator"),
                    ft.dropdown.Option("AdminViewer"),
                    ft.dropdown.Option("Admin"),
                ]
            )

            def save_edit(e):
                new_pass = edit_pass.value if edit_pass.value else getattr(user, "password", None)
                try:
                    success, msg = admin_service.update_user(
                        user.id,
                        edit_name.value,
                        edit_user.value,
                        new_pass,
                        edit_role.value
                    )
                except AttributeError:
                    page.open(ft.SnackBar(
                        ft.Text("Backend missing update_user(). Add it to services/admin_service.py"),
                        bgcolor=ft.Colors.ORANGE
                    ))
                    return

                if success:
                    page.open(ft.SnackBar(ft.Text("User Updated!"), bgcolor=ft.Colors.GREEN))
                    page.close(edit_dialog)
                    load_users_view()
                else:
                    page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED))

            edit_dialog = ft.AlertDialog(
                title=ft.Text("Edit User"),
                content=ft.Column([edit_name, edit_user, edit_pass, edit_role], height=260),
                actions=[ft.TextButton("Save", on_click=save_edit)]
            )

            page.open(edit_dialog)

        # TABLE LAYOUT
        TABLE_WIDTH = 850   # Increased width to prevent collapsing
        table_rows = []

        for u in users:

            # EDIT BUTTON
            action_btn = ft.TextButton(
                "Edit",
                data=u.id,
                icon=ft.Icons.EDIT,
                style=ft.ButtonStyle(color=ft.Colors.BLUE),
                on_click=open_edit_dialog
            )

            # DELETE BUTTON
            delete_icon = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ft.Colors.RED,
                data=u.id,
                on_click=open_delete_dialog,
                tooltip="Delete User"
            )

            # ROW FOR EACH USER
            row = ft.Container(
                width=TABLE_WIDTH,
                bgcolor=ft.Colors.WHITE,
                border_radius=8,
                padding=10,
                margin=ft.margin.only(bottom=8),
                shadow=ft.BoxShadow(blur_radius=6, spread_radius=1, color=ft.Colors.GREY_300),
                content=ft.Row(
                    [
                        ft.Container(ft.Text(str(u.id)), width=60),
                        ft.Container(ft.Text(u.name), width=220),
                        ft.Container(ft.Text(u.role), width=180),
                        ft.Container(ft.Text(u.username), width=180),

                        # FIXED ACTION AREA (WIDER)
                        ft.Container(
                            ft.Row(
                                [
                                    action_btn,
                                    delete_icon,
                                ],
                                spacing=20,
                                alignment=ft.MainAxisAlignment.START
                            ),
                            width=240,     # <–– WIDER so delete button is visible
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START
                )
            )

            table_rows.append(row)

        # HEADER ROW
        table_header = ft.Container(
            width=TABLE_WIDTH,
            bgcolor=ft.Colors.BLUE_100,
            padding=10,
            border_radius=8,
            content=ft.Row([
                ft.Container(ft.Text("ID", weight="bold"), width=60),
                ft.Container(ft.Text("Name", weight="bold"), width=220),
                ft.Container(ft.Text("Role", weight="bold"), width=180),
                ft.Container(ft.Text("Username", weight="bold"), width=180),
                ft.Container(ft.Text("Action", weight="bold"), width=240),
            ])
        )

        # MAIN CONTENT AREA
        main_content_area.content = ft.Column(
            [
                ft.Row([hamburger_btn, ft.Text("Manage Users", size=24, weight="bold")]),
                ft.ElevatedButton("Add New User", icon=ft.Icons.ADD, on_click=open_add_user_dialog),
                ft.Divider(),
                ft.Row([table_header], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([ft.Column(table_rows, scroll="adaptive")], alignment=ft.MainAxisAlignment.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        page.update()

    # ---------------------------------------------------------
    # EVENTS VIEW (unchanged)
    # ---------------------------------------------------------
    def load_events_view():
        sidebar_container.visible = False
        events = admin_service.get_all_events()

        events_grid = ft.GridView(
            runs_count=2,
            max_extent=300,
            child_aspect_ratio=1.5,
            spacing=10,
            run_spacing=10,
        )

        for e in events:

            # ========= EVENT TYPE SETTINGS =========
            if e.event_type == "Pageant":
                background_image = ft.DecorationImage(
                    src="pageant.png",
                    fit=ft.ImageFit.COVER,
                )
                title_color = ft.Colors.WHITE
                subtitle_color = ft.Colors.AMBER_200
                icon = ft.Icons.WOMAN

            elif e.event_type == "QuizBee":
                background_image = ft.DecorationImage(
                    src="quiz.png",
                    fit=ft.ImageFit.COVER,
                )
                title_color = ft.Colors.WHITE
                subtitle_color = ft.Colors.YELLOW
                icon = ft.Icons.LIGHTBULB

            else:
                background_image = None
                title_color = ft.Colors.BLACK
                subtitle_color = ft.Colors.GREY
                icon = ft.Icons.EVENT

            # ========= MANAGE BUTTON =========
            manage_btn = ft.ElevatedButton(
                "Manage",
                data=e.id,
                on_click=lambda ev: page.go(f"/admin/event/{ev.control.data}")
            )

            # ========= CARD CONTENT (NO GLASS EFFECT) =========
            card_content = ft.Container(
                padding=15,
                content=ft.Column(
                    [
                        ft.Row([
                            ft.Icon(icon, color=subtitle_color),
                            ft.Text(e.event_type, color=subtitle_color, weight="bold")
                        ]),
                        ft.Text(e.name, size=18, weight="bold", color=title_color),
                        ft.Text(f"Status: {e.status}", color=title_color),
                        manage_btn
                    ],
                    spacing=8
                )
            )

            # ========= CARD WITH BACKGROUND =========
            card = ft.Container(
                border_radius=10,
                image=background_image,
                padding=0,
                bgcolor=None,  # fully transparent
                content=ft.Container(
                    expand=True,
                    padding=10,
                    content=card_content
                )
            )

            events_grid.controls.append(card)

        main_content_area.content = ft.Column([
            ft.Row([hamburger_btn, ft.Text("Manage Events", size=24, weight="bold")]),
            ft.ElevatedButton("Create Event", icon=ft.Icons.ADD, on_click=open_add_event_dialog),
            ft.Divider(),
            ft.Container(content=events_grid, expand=True)
        ], expand=True)

        page.update()

    # ---------------------------------------------------------
    # NAVIGATION RAIL
    # ---------------------------------------------------------
    def nav_change(e):
        index = e.control.selected_index
        if index == 0:
            load_welcome_view()
        elif index == 1:
            load_users_view()
        elif index == 2:
            load_events_view()
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        expand=True,
        bgcolor=ft.Colors.BLUE_GREY_50,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.PEOPLE, label="Users"),
            ft.NavigationRailDestination(icon=ft.Icons.CALENDAR_TODAY, label="Events"),
        ],
        on_change=nav_change,
    )

    close_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        icon_color="black",
        on_click=close_sidebar
    )

    logout_btn = ft.Container(
        content=ft.ElevatedButton(
            "Logout",
            icon=ft.Icons.LOGOUT,
            on_click=on_logout_callback,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            width=230
        ),
        padding=10,
    )

    sidebar_container.content = ft.Column(
        controls=[
            ft.Row([ft.Container(expand=True), close_btn]),
            rail,
            ft.Divider(),
            logout_btn
        ],
        spacing=0,
        expand=True
    )

    # ---------------------------------------------------------
    # WELCOME VIEW
    # ---------------------------------------------------------
    def load_welcome_view():
        sidebar_container.visible = False
        
        content = ft.Column([
            ft.Row([hamburger_btn, ft.Text("Admin Dashboard", size=30, weight="bold")]),
            ft.Text("Select an option from the menu to get started.", size=16),
            ft.Divider(),
            ft.Container(
                padding=20,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=10,
                content=ft.Column([
                    ft.Text("Quick Stats", weight="bold"),
                    ft.Text("System Status: Online"),
                    ft.Text("Database: Connected")
                ])
            )
        ])
        main_content_area.content = content
        page.update()

    load_welcome_view()

    # RETURN LAYOUT
    return ft.Column(
        expand=True,
        controls=[
            header,
            ft.Row(
                expand=True,
                controls=[
                    sidebar_container,
                    ft.VerticalDivider(width=1),
                    main_content_area
                ]
            )
        ]
    )
