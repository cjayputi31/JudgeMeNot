import flet as ft
from services.auth_service import AuthService

def SignupView(page: ft.Page):
    auth_service = AuthService()
    
    name_field = ft.TextField(label="Full Name", width=300, autofocus=True)
    user_field = ft.TextField(label="Username", width=300)
    pass_field = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
    
    role_dropdown = ft.Dropdown(
        label="I am applying as...", width=300,
        options=[ft.dropdown.Option("Judge"), ft.dropdown.Option("Tabulator")]
    )

    def on_signup_click(e):
        if not role_dropdown.value or not all([name_field.value, user_field.value, pass_field.value]):
            page.snack_bar = ft.SnackBar(ft.Text("Please fill out all fields."), bgcolor="red")
            page.snack_bar.open = True; page.update(); return
        
        success, msg = auth_service.register_self_service(
            name=name_field.value, username=user_field.value, password=pass_field.value, role=role_dropdown.value
        )

        if success:
            dialog = ft.AlertDialog(
                modal=True, title=ft.Text("Registration Successful"),
                content=ft.Text("Your account has been created and is PENDING ADMIN APPROVAL.\n\nPlease contact your Admin to activate your account."),
                actions=[ft.TextButton("Back to Login", on_click=lambda x: page.go("/login"))],
                on_dismiss=lambda x: page.go("/login")
            )
            page.open(dialog)
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"); page.snack_bar.open=True; page.update()

    return ft.Container(
        expand=True, alignment=ft.alignment.center,
        content=ft.Card(content=ft.Container(padding=40, content=ft.Column([
            ft.Text("Create Account", size=24, weight="bold"),
            ft.Text("For Judges & Tabulators Only", size=12, color="grey"),
            ft.Divider(),
            name_field, user_field, pass_field, role_dropdown,
            ft.Container(height=10),
            ft.ElevatedButton("Request Account", on_click=on_signup_click, bgcolor="green", color="white", width=300),
            ft.TextButton("Already have an account? Login", on_click=lambda e: page.go("/login"))
        ], horizontal_alignment="center")))
    )