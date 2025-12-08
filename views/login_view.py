"""
Login Screen using Flet - Ultra Clean Version
"""

import flet as ft
from services.auth_service import AuthService
# Updated imports to include dialogs
from components.dialogs import show_about_dialog, show_contact_dialog

def LoginView(page: ft.Page, on_login_success_callback):
    auth = AuthService()
    page.bgcolor = ft.Colors.WHITE
    page.assets_dir = "assets"

    # ---------------------- CUSTOM HEADER ----------------------
    # Replaced shared 'create_header' with a custom one to include Leaderboard/About/Contact
    
    header_logo = ft.Container(
        width=40, height=40, border_radius=50, bgcolor="transparent",
        border=ft.border.all(2, ft.Colors.BLUE_800), padding=5,
        content=ft.Image(src="hammer.png", fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.GAVEL, color=ft.Colors.BLUE_800))
    )

    header = ft.Container(
        height=70, 
        padding=ft.padding.symmetric(horizontal=40), 
        bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.GREY_300),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                # Left: Logo & Title
                ft.Row(spacing=10, controls=[
                    header_logo, 
                    ft.Text("JUDGEMENOT", size=20, weight="bold", color=ft.Colors.BLUE_900)
                ]),
                
                # Right: Public Navigation
                ft.Row(spacing=5, controls=[
                    ft.TextButton("LEADERBOARD", icon=ft.Icons.EMOJI_EVENTS, style=ft.ButtonStyle(color=ft.Colors.BLUE_800), on_click=lambda e: page.go("/leaderboard")),
                    ft.TextButton("ABOUT", style=ft.ButtonStyle(color=ft.Colors.GREY_700), on_click=lambda e: show_about_dialog(page)),
                    ft.TextButton("CONTACT", style=ft.ButtonStyle(color=ft.Colors.GREY_700), on_click=lambda e: show_contact_dialog(page)),
                ])
            ]
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

    # ---------------------- CLICKABLE HANDLERS ----------------------
    def forgot_password_clicked(e):
        """Handle forgot password - redirect to forgot password page"""
        print("Navigating to forgot password page...")
        page.go("/forgot-password")  # You'll need to create this route

    def signup_clicked(e):
        """Handle sign up - redirect to signup page"""
        print("Navigating to signup page...")
        page.go("/signup")  # You'll need to create this route

    def google_login_clicked(e):
        """Handle Google/CSPC login"""
        print("CSPC Mail login clicked...")
        # Add your Google OAuth logic here
        page.open(ft.SnackBar(ft.Text("Google login coming soon!"), bgcolor=ft.Colors.BLUE))

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
        padding=30,
        bgcolor="#C9E4FF",
        border_radius=20,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,  # Enable scrolling if content overflows
            controls=[
                ft.Text("Welcome Back!", size=32, weight="bold", color=ft.Colors.BLACK),

                user_input,
                pass_input,

                # Clickable Forgot Password Link
                ft.TextButton(
                    "Forgotten your username or password?",
                    style=ft.ButtonStyle(color=ft.Colors.BLUE_700),
                    on_click=forgot_password_clicked,
                ),

                error_text,

                # Login Button - Uses ElevatedButton for better click handling
                ft.ElevatedButton(
                    "Login",
                    width=160,
                    height=42,
                    bgcolor="#64AEFF",
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=30),
                    ),
                    on_click=login_clicked,
                ),

                # Clickable Sign Up Link
                ft.Row(
                    spacing=5,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Need an account?", size=12),
                        ft.TextButton(
                            "Sign up",
                            style=ft.ButtonStyle(
                                color=ft.Colors.BLUE_700,
                                padding=0,
                            ),
                            on_click=signup_clicked,
                        ),
                    ],
                ),

                ft.Container(
                    width=350,
                    height=1,
                    bgcolor=ft.Colors.BLUE_200,
                    margin=ft.margin.only(top=5, bottom=5),
                ),

                ft.Text("Log in using your account on:", size=12, color=ft.Colors.BLACK),

                # Clickable CSPC Mail Button - Better click handling
                ft.ElevatedButton(
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                        controls=[
                            ft.Image(
                                src="google.png",
                                width=22,
                                height=22
                            ),
                            ft.Text("CSPC Mail", size=14, color=ft.Colors.BLACK),
                        ],
                    ),
                    width=320,
                    height=45,
                    bgcolor=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        side=ft.BorderSide(1, ft.Colors.GREY_300),
                        overlay_color=ft.Colors.BLUE_50,  # Hover effect
                    ),
                    on_click=google_login_clicked,
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