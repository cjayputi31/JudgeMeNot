"""
I need you to build the Login Screen using Flet. 
It needs a Username field, a Password field (masked), and a 'Login' button. When the button is clicked, 
it should check if the fields are empty. If not, print 'Attempting login...' to the console. 
Don't worry about the database connection yet; I will wire that up.

We will stick to Standard Login first to ensure the core tabulation works. 
If we have time in the final week, we will add the Google Login button as an enhancement.
"""

import flet as ft
from services.auth_service import AuthService

def LoginView(page: ft.Page, on_login_success_callback):
    auth = AuthService()
    page.bgcolor = ft.Colors.WHITE

    # VERY IMPORTANT so your local PNG loads
    page.assets_dir = "assets"

    # ---------------------- HEADER BAR ----------------------
    def about_clicked(e):
        print("ABOUT clicked")

    def contact_clicked(e):
        print("CONTACT clicked")

    # ---- CIRCULAR ROUNDED HAMMER LOGO ----
    logo = ft.Container(
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
            logo,
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

    # ---------------------- INPUT FIELDS ----------------------
    user_input = ft.TextField(
        hint_text="Username",
        width=320,
        height=48,
        border_radius=8,
        border_color=ft.Colors.BLUE_100,
        bgcolor=ft.Colors.WHITE,
        content_padding=ft.padding.only(left=15, right=15),
    )

    pass_input = ft.TextField(
        hint_text="Password",
        password=True,
        can_reveal_password=True,
        width=320,
        height=48,
        border_radius=8,
        border_color=ft.Colors.BLUE_100,
        bgcolor=ft.Colors.WHITE,
        content_padding=ft.padding.only(left=15, right=15),
    )

    error_text = ft.Text("", color="red", size=12)

    # ---------------------- LOGIN CLICK ----------------------
    def login_clicked(e):
        username = user_input.value
        password = pass_input.value

        if not username or not password:
            error_text.value = "Please fill all fields."
            error_text.update()
            return

        print("Attempting login...")

        user = auth.login(username, password)

        if user == "DISABLED":
            error_text.value = "Account is disabled. Contact Admin."
            error_text.update()
        elif user:
            on_login_success_callback(user)
        else:
            error_text.value = "Invalid username or password."
            error_text.update()

    # ---------------------- LOGIN BOX ----------------------
    login_box = ft.Container(
        width=650,
        height=480,
        padding=30,
        bgcolor="#C9E4FF",
        border_radius=20,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Text("Welcome Back!", size=32, weight="bold", color=ft.Colors.BLACK),

                user_input,
                pass_input,

                ft.Text(
                    "Forgotten your username or password?",
                    size=12,
                    color=ft.Colors.BLUE_700,
                ),

                error_text,

                ft.Container(
                    width=160,
                    height=42,
                    border_radius=30,
                    bgcolor="#64AEFF",
                    alignment=ft.alignment.center,
                    on_click=login_clicked,
                    content=ft.Text("Login", color=ft.Colors.WHITE, size=16, weight="bold"),
                ),

                ft.Row(
                    spacing=5,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Need an account?", size=12),
                        ft.Text("Sign up", size=12, color=ft.Colors.BLUE_700, weight="bold"),
                    ],
                ),

                ft.Container(
                    width=350,
                    height=1,
                    bgcolor=ft.Colors.BLUE_200,
                    margin=ft.margin.only(top=5, bottom=5),
                ),

                ft.Text("Log in using your account on:", size=12, color=ft.Colors.BLACK),

                # ---------------------------------------------
                # LOCAL GOOGLE PNG (NO MORE NETWORK IMAGE)
                # ---------------------------------------------
                ft.Container(
                    width=320,
                    height=45,
                    border_radius=8,
                    bgcolor=ft.Colors.WHITE,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    alignment=ft.alignment.center,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                        controls=[
                            ft.Image(
                                src="google.png",   # local asset
                                width=22,
                                height=22
                            ),
                            ft.Text("CSPC Mail", size=14, color=ft.Colors.BLACK),
                        ],
                    ),
                ),
            ],
        )
    )

    # ---------------------- MAIN LAYOUT ----------------------
    return ft.Column(
        expand=True,
        controls=[
            header,
            ft.Container(
                expand=True,
                alignment=ft.alignment.center,
                content=login_box
            )
        ]
    )
