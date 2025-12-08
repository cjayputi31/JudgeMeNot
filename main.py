import flet as ft
import socket
import os
from flet.auth.providers import GoogleOAuthProvider
from services.auth_service import AuthService
from core.database import SessionLocal

# Views
from views.login_view import LoginView
from views.signup_view import SignupView
from views.account_setup_view import AccountSetupView
from views.admin_dashboard import AdminDashboardView
from views.admin_config_view import AdminConfigView
from views.judge_view import JudgeView
from views.tabulator_view import TabulatorView
from views.viewer_dashboard import EventListView, EventLeaderboardView

def on_google_login(page: ft.Page, auth_service):
    if page.auth.error:
        page.snack_bar = ft.SnackBar(ft.Text("Google Login Failed"), bgcolor="red")
        page.snack_bar.open=True; page.update(); return

    g_id = page.auth.user.get("id")
    user = auth_service.get_user_by_google_id(g_id)
    
    if user:
        if user.is_pending:
             page.snack_bar = ft.SnackBar(ft.Text("Account Pending Approval"), bgcolor="red")
             page.snack_bar.open=True; page.update(); page.logout(); return
        
        page.session.set("user_id", user.id)
        page.session.set("user_role", user.role)
        page.session.set("user_name", user.name)
        page.go(f"/{user.role.lower()}")
    else:
        # Pass data to setup
        page.client_storage.set("google_id", g_id)
        page.client_storage.set("google_email", page.auth.user.get("email"))
        page.client_storage.set("google_name", page.auth.user.get("name"))
        page.go("/account-setup")

def main(page: ft.Page):
    page.title = "JudgeMeNot"
    page.theme_mode = ft.ThemeMode.LIGHT
    auth_service = AuthService()

    
    # SETUP GOOGLE
    # Get these from Google Cloud Console
    CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID_HERE") 
    CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")
    
    google_provider = GoogleOAuthProvider(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_url="http://localhost:8550/api/oauth/redirect"
    )
    page.client_storage.set("google_provider", google_provider)
    page.on_login = lambda e: on_google_login(page, auth_service)

    def route_change(route):
        page.views.clear()
        uid = page.session.get("user_id")
        role = page.session.get("user_role")

        if page.route == "/login":
            page.views.append(ft.View("/login", [LoginView(page, on_login_success)]))
        elif page.route == "/signup":
            page.views.append(ft.View("/signup", [SignupView(page)]))
        elif page.route == "/account-setup":
            page.views.append(ft.View("/account-setup", [AccountSetupView(page)]))
        elif page.route == "/admin" and role == "Admin":
            page.views.append(ft.View("/admin", [AdminDashboardView(page, on_logout)]))
        elif page.route.startswith("/admin/event/") and role == "Admin":
            eid = int(page.route.split("/")[-1])
            page.views.append(ft.View(f"/admin/event/{eid}", [AdminConfigView(page, eid)]))
        elif page.route == "/judge" and role == "Judge":
            page.views.append(ft.View("/judge", [JudgeView(page, on_logout)]))
        elif page.route == "/tabulator" and role == "Tabulator":
            page.views.append(ft.View("/tabulator", [TabulatorView(page, on_logout)]))
        elif page.route == "/leaderboard":
            page.views.append(ft.View("/leaderboard", [EventListView(page)]))
        elif page.route.startswith("/leaderboard/"):
            eid = int(page.route.split("/")[-1])
            page.views.append(ft.View(f"/leaderboard/{eid}", [EventLeaderboardView(page, eid)]))
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
        page.go(f"/{user.role.lower()}")

    def on_logout(e):
        page.session.clear()
        page.go("/login")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/login")

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