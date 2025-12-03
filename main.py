import flet as ft
from services.auth_service import AuthService
from views.login_view import LoginView
from views.admin_dashboard import AdminDashboardView
from views.admin_config_view import AdminConfigView

def main(page: ft.Page):
    page.title = "JudgeMeNot System"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    auth_service = AuthService()

    def route_change(route):
        page.views.clear()
        
        user_id = page.session.get("user_id")
        user_role = page.session.get("user_role")

        # --- ROUTE: LOGIN ---
        if page.route == "/login" or page.route == "/":
            page.views.append(
                ft.View(
                    "/login",
                    [LoginView(page, on_login_success)],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )

        # --- ROUTE: ADMIN DASHBOARD ---
        elif page.route == "/admin":
            if user_id and user_role in ["Admin", "AdminViewer"]:
                page.views.append(
                    ft.View("/admin", [AdminDashboardView(page, on_logout)])
                )
            else:
                page.go("/login")
        
        # --- ROUTE: EVENT CONFIGURATION (Dynamic ID) ---
        # Pattern: /admin/event/5
        elif page.route.startswith("/admin/event/"):
            if user_id and user_role == "Admin": # Only Admins edit config
                try:
                    # Parse ID from URL string
                    event_id = int(page.route.split("/")[-1])
                    page.views.append(
                        ft.View(
                            f"/admin/event/{event_id}",
                            [AdminConfigView(page, event_id)]
                        )
                    )
                except ValueError:
                    page.snack_bar = ft.SnackBar(ft.Text("Invalid Event ID"))
                    page.go("/admin")
            else:
                page.go("/login")

        # --- CATCH ALL ---
        else:
            page.go("/login")

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    def on_login_success(user):
        page.session.set("user_id", user.id)
        page.session.set("user_role", user.role)
        page.session.set("user_name", user.name)
        
        if user.role == "Admin":
            page.go("/admin")
        else:
            page.go("/login") # Add Judge/Tabulator logic later

    def on_logout(e):
        page.session.clear()
        page.go("/login")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)

if __name__ == "__main__":
    ft.app(target=main)