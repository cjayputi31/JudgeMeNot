import flet as ft
import socket # Required for IP detection
from services.auth_service import AuthService
from views.login_view import LoginView
from views.admin_dashboard import AdminDashboardView
from views.admin_config_view import AdminConfigView
from views.judge_view import JudgeView
from views.tabulator_view import TabulatorView 

def main(page: ft.Page):
    page.title = "JudgeMeNot System"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.assets_dir = "assets"

    # --- WINDOW SETTINGS ---
    page.window.min_width = 900
    page.window.min_height = 675
    page.window.center() 

    auth_service = AuthService()

    # --- NAVIGATION GUARD ---
    # Prevents 'view_pop' from firing during programmatic navigation
    page.is_navigating = False 

    def route_change(route):
        page.is_navigating = True # Start Navigation Lock
        
        # 1. Clear previous views
        page.views.clear()
        # 2. Clear overlays (Dialogs)
        page.overlay.clear()

        user_id = page.session.get("user_id")
        user_role = page.session.get("user_role")

        print(f"🚗 Navigating to: {page.route} | User: {user_role}")

        # --- ROUTE: LOGIN ---
        if page.route == "/login" or page.route == "/":
            page.views.append(
                ft.View(
                    "/login",
                    [LoginView(page, on_login_success)],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    padding=0
                )
            )
        
        # --- ROUTE: ADMIN DASHBOARD ---
        elif page.route == "/admin":
            if user_id and user_role in ["Admin", "AdminViewer"]:
                page.views.append(
                    ft.View(
                        "/admin", 
                        [AdminDashboardView(page, on_logout)],
                        padding=0 
                    )
                )
            else:
                page.go("/login")

        # --- ROUTE: EVENT CONFIGURATION ---
        elif page.route.startswith("/admin/event/"):
            if user_id and user_role == "Admin": 
                try:
                    event_id = int(page.route.split("/")[-1])
                    page.views.append(
                        ft.View(
                            f"/admin/event/{event_id}",
                            [AdminConfigView(page, event_id)],
                            padding=0
                        )
                    )
                except ValueError:
                    page.go("/admin")
            else:
                page.go("/login")

        # --- ROUTE: JUDGE INTERFACE ---
        elif page.route == "/judge":
            if user_id and user_role == "Judge":
                page.views.append(
                    ft.View(
                        "/judge", 
                        [JudgeView(page, on_logout)],
                        padding=0
                    )
                )
            else:
                page.go("/login")
        
        # --- ROUTE: TABULATOR ---
        elif page.route == "/tabulator":
             if user_id and user_role == "Tabulator":
                page.views.append(
                    ft.View(
                        "/tabulator",
                        [TabulatorView(page, on_logout)],
                        padding=0
                    )
                )
             else:
                page.go("/login")

        # --- CATCH ALL ---
        else:
            page.go("/login")

        page.update()
        page.is_navigating = False # Release Lock after update

    def view_pop(view):
        # If we are in the middle of a route change, IGNORE pop events
        if getattr(page, 'is_navigating', False):
            return

        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)
        else:
            print("⚠️ Root view reached. Ignoring pop.")

    def on_login_success(user):
        page.session.set("user_id", user.id)
        page.session.set("user_role", user.role)
        page.session.set("user_name", user.name)

        if user.role == "Admin":
            page.go("/admin")
        elif user.role == "Judge":
            page.go("/judge")
        elif user.role == "Tabulator":
            page.go("/tabulator")
        else:
            page.go("/login")

    def on_logout(e):
        print("👋 Logging out...")
        page.session.clear()
        page.go("/login")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Initialize app
    page.go(page.route)

# --- HELPER: GET LOCAL IP ---
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    my_ip = get_local_ip()
    port = 8550
    print(f"--------------------------------------------------")
    print(f"🚀  JUDGE ME NOT SYSTEM IS RUNNING!")
    print(f"📱  Judges connect here: http://{my_ip}:{port}")
    print(f"💻  Local Access:        http://127.0.0.1:{port}")
    print(f"--------------------------------------------------")

    # We pass '0.0.0.0' to host to bind to ALL interfaces, 
    # but we print the specific IP above for user convenience.

    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host=my_ip)
    # ft.app(target=main)