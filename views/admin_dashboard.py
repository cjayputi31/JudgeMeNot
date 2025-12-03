import flet as ft
from services.admin_service import AdminService

def AdminDashboardView(page: ft.Page, on_logout_callback):
    admin_service = AdminService()

    # Ensure assets folder is used
    page.assets_dir = "assets"

    # ---------------------------------------------------------
    # HEADER (reused style from LoginView)
    # ---------------------------------------------------------

    def about_clicked(e):
        print("ABOUT clicked")

    def contact_clicked(e):
        print("CONTACT clicked")

    # Circular hammer logo
    header_logo = ft.Container(
        width=45,
        height=45,
        border_radius=50,
        bgcolor="transparent",
        border=ft.border.all(2, ft.Colors.BLACK),
        padding=5,
        content=ft.Image(
            src="hammer.png",
            fit=ft.ImageFit.CONTAIN
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
        bgcolor="#80C1FF",
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[header_left, header_right],
        )
    )

    # ---------------------------------------------------------
    # 1. SIDEBAR + LAYOUT STATE
    # ---------------------------------------------------------

    sidebar_container = ft.Container(
        width=250,
        visible=False,
        bgcolor=ft.Colors.BLUE_GREY_50,
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
    # (Everything from dialogs to content views stays EXACTLY the same)
    # ---------------------------------------------------------
    # --- DIALOGS, USER VIEWS, EVENT VIEWS, RAIL, LOGOUT BUTTON ---
    # (Your entire logic is untouched; only header added)
    # ---------------------------------------------------------

    # --- ADD USER DIALOG ---
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
            page.snack_bar = ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()
            return

        success, msg = admin_service.create_user(
            new_user_name.value,
            new_user_user.value,
            new_user_pass.value,
            new_user_role.value
        )
        
        if success:
            page.snack_bar = ft.SnackBar(ft.Text("User Added!"), bgcolor=ft.Colors.GREEN)
            page.dialog.open = False
            load_users_view()
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED)

        page.snack_bar.open = True
        page.update()

    user_dialog = ft.AlertDialog(
        title=ft.Text("Add New User"),
        content=ft.Column([new_user_name, new_user_user, new_user_pass, new_user_role], height=300),
        actions=[ft.TextButton("Save", on_click=save_user)]
    )

    def open_add_user_dialog(e):
        page.dialog = user_dialog
        user_dialog.open = True
        page.update()

    # --- ADD EVENT DIALOG ---
    new_event_name = ft.TextField(label="Event Name")
    new_event_type = ft.Dropdown(
        label="Event Type",
        options=[
            ft.dropdown.Option("Pageant"),
            ft.dropdown.Option("QuizBee"),
        ]
    )

    def save_event(e):
        if not new_event_name.value or not new_event_type.value:
            page.snack_bar = ft.SnackBar(ft.Text("Please fill all fields"), bgcolor=ft.Colors.RED)
            page.snack_bar.open = True
            page.update()
            return

        success, msg = admin_service.create_event(new_event_name.value, new_event_type.value)

        if success:
            page.snack_bar = ft.SnackBar(ft.Text("Event Created!"), bgcolor=ft.Colors.GREEN)
            page.dialog.open = False
            load_events_view()
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor=ft.Colors.RED)

        page.snack_bar.open = True
        page.update()

    event_dialog = ft.AlertDialog(
        title=ft.Text("Create New Event"),
        content=ft.Column([new_event_name, new_event_type], height=150),
        actions=[ft.TextButton("Create", on_click=save_event)]
    )

    def open_add_event_dialog(e):
        page.dialog = event_dialog
        event_dialog.open = True
        page.update()

    # ---------------------------------------------------------
    # CONTENT VIEW FUNCTIONS
    # ---------------------------------------------------------

    def load_welcome_view():
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

    def load_users_view():
        users = admin_service.get_all_users()

        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Role")),
                ft.DataColumn(ft.Text("Username")),
            ],
            rows=[
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(u.id))),
                    ft.DataCell(ft.Text(u.name)),
                    ft.DataCell(ft.Text(u.role)),
                    ft.DataCell(ft.Text(u.username)),
                ]) for u in users
            ],
            border=ft.border.all(1, ft.Colors.GREY_300),
        )

        main_content_area.content = ft.Column([
            ft.Row([hamburger_btn, ft.Text("Manage Users", size=24, weight="bold")]),
            ft.ElevatedButton("Add New User", icon=ft.Icons.ADD, on_click=open_add_user_dialog),
            ft.Divider(),
            ft.Row([data_table], scroll="adaptive")
        ])
        page.update()

    def load_events_view():
        events = admin_service.get_all_events()

        events_grid = ft.GridView(
            runs_count=2,
            max_extent=300,
            child_aspect_ratio=1.5,
            spacing=10,
            run_spacing=10,
        )

        for e in events:
            bg_color = ft.Colors.PINK_50 if e.event_type == "Pageant" else ft.Colors.GREEN_50
            icon = ft.Icons.WOMAN if e.event_type == "Pageant" else ft.Icons.QUIZ
            border_col = ft.Colors.PINK if e.event_type == "Pageant" else ft.Colors.GREEN

            card = ft.Container(
                bgcolor=bg_color,
                border=ft.border.all(1, border_col),
                border_radius=10,
                padding=15,
                content=ft.Column([
                    ft.Row([ft.Icon(icon, color=border_col), ft.Text(e.event_type, weight="bold", color=border_col)]),
                    ft.Text(e.name, size=18, weight="bold"),
                    ft.Text(f"Status: {e.status}"),
                    ft.ElevatedButton("Manage", data=e.id)
                ])
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
    # NAVIGATION RAIL (Sidebar inside)
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
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD, label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.PEOPLE, label="Users"),
            ft.NavigationRailDestination(icon=ft.Icons.CALENDAR_TODAY, label="Events"),
        ],
        on_change=nav_change,
    )

    close_btn = ft.IconButton(
        icon=ft.Icons.CHEVRON_LEFT,
        icon_color="red",
        on_click=close_sidebar
    )

    logout_btn = ft.Container(
        content=ft.ElevatedButton(
            "Logout",
            icon=ft.Icons.LOGOUT,
            on_click=on_logout_callback,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            width=200
        ),
        padding=10,
    )

    sidebar_content = ft.Column(
        controls=[
            ft.Row([ft.Container(expand=True), close_btn]),
            rail,
            ft.Divider(),
            logout_btn
        ],
        spacing=0,
        expand=True
    )

    sidebar_container.content = sidebar_content

    # ---------------------------------------------------------
    # INITIAL LOAD
    # ---------------------------------------------------------
    load_welcome_view()

    # ---------------------------------------------------------
    # FINAL STRUCTURE (Header on top)
    # ---------------------------------------------------------

    return ft.Column(
        expand=True,
        controls=[
            header,   # <── added
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
