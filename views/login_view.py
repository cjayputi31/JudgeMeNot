import flet as ft
from services.auth_service import AuthService
from components.dialogs import show_about_dialog, show_contact_dialog

def LoginView(page: ft.Page, on_login_success_callback):
    auth = AuthService()
    page.bgcolor = ft.Colors.WHITE
    page.assets_dir = "assets"

    header_logo = ft.Container(
        width=40, height=40, border_radius=50, bgcolor="transparent",
        border=ft.border.all(2, ft.Colors.BLUE_800), padding=5,
        content=ft.Image(src="hammer.png", fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.GAVEL, color=ft.Colors.BLUE_800))
    )

    header = ft.Container(
        height=70, padding=ft.padding.symmetric(horizontal=40), bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(blur_radius=5, color=ft.Colors.GREY_300),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(spacing=10, controls=[header_logo, ft.Text("JUDGEMENOT", size=20, weight="bold", color=ft.Colors.BLUE_900)]),
                ft.Row(spacing=5, controls=[
                    ft.TextButton("LEADERBOARD", icon=ft.Icons.EMOJI_EVENTS, style=ft.ButtonStyle(color=ft.Colors.BLUE_800), on_click=lambda e: page.go("/leaderboard")),
                    ft.TextButton("ABOUT", style=ft.ButtonStyle(color=ft.Colors.GREY_700), on_click=lambda e: show_about_dialog(page)),
                    ft.TextButton("CONTACT", style=ft.ButtonStyle(color=ft.Colors.GREY_700), on_click=lambda e: show_contact_dialog(page)),
                ])
            ]
        )
    )

    user_input = ft.TextField(hint_text="Username", width=320, height=48, border_radius=8, bgcolor=ft.Colors.WHITE)
    pass_input = ft.TextField(hint_text="Password", password=True, can_reveal_password=True, width=320, height=48, border_radius=8, bgcolor=ft.Colors.WHITE)
    error_text = ft.Text("", color="red", size=12)

    def forgot_password_clicked(e):
        page.client_storage.remove("user_id") 
        info_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Password Recovery Policy"),
            content=ft.Column([
                # Swapped to LOCK_OPEN to ensure compatibility
                ft.Icon(ft.Icons.LOCK_OPEN, size=50, color=ft.Colors.BLUE_700),
                ft.Text("For security reasons, please contact your System Administrator.\nThey can reset your password via the Admin Dashboard.")
            ], tight=True, horizontal_alignment="center", width=350),
            actions=[ft.TextButton("OK", on_click=lambda e: page.close(info_dialog))]
        )
        page.open(info_dialog)

    def login_clicked(e):
        if not user_input.value or not pass_input.value:
            error_text.value = "Please fill all fields."; error_text.update(); return
        
        user = auth.login(user_input.value, pass_input.value)
        if user == "DISABLED":
            error_text.value = "Account is disabled."; error_text.update()
        elif user == "PENDING":
             error_text.value = "Account pending Admin approval."; error_text.update()
        elif user:
            on_login_success_callback(user)
        else:
            error_text.value = "Invalid credentials."; error_text.update()

    def on_google_login_click(e):
        google_provider = page.client_storage.get("google_provider") 
        if google_provider:
             page.login(google_provider)
        else:
             page.snack_bar = ft.SnackBar(ft.Text("Google provider not configured."), bgcolor="red"); page.snack_bar.open=True; page.update()

    login_box = ft.Container(
        width=650, padding=30, bgcolor="#C9E4FF", border_radius=20,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12,
            controls=[
                ft.Text("Welcome Back!", size=32, weight="bold", color=ft.Colors.BLACK),
                user_input, pass_input,
                ft.TextButton("Forgot password?", style=ft.ButtonStyle(color=ft.Colors.BLUE_700), on_click=forgot_password_clicked),
                error_text,
                ft.ElevatedButton("Login", width=160, height=42, bgcolor="#64AEFF", color=ft.Colors.WHITE, on_click=login_clicked),
                
                ft.Divider(height=25, color=ft.Colors.BLACK54),
                ft.Text("OR"),
                # FIXED: Changed ft.Icons.ATTRIBUTES to ft.Icons.LOGIN
                ft.ElevatedButton("Sign in with Google", icon=ft.Icons.LOGIN, on_click=on_google_login_click, width=300, bgcolor=ft.Colors.WHITE, color=ft.Colors.BLACK),
                ft.TextButton("Create a Judge/Tabulator Account", on_click=lambda e: page.go("/signup"))
            ]
        )
    )

    return ft.Column(expand=True, controls=[header, ft.Container(expand=True, alignment=ft.alignment.center, content=login_box)])