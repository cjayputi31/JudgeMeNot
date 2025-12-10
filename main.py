import flet as ft
import socket
import os
from dotenv import load_dotenv 
from services.auth_service import AuthService
from core.database import SessionLocal

# Views
from views.login_view import LoginView
from views.signup_view import SignupView
from views.admin_dashboard import AdminDashboardView
from views.admin_config_view import AdminConfigView
from views.judge_view import JudgeView
from views.tabulator_view import TabulatorView
from views.viewer_dashboard import EventListView, EventLeaderboardView

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv() 
# ----------------------------------

def main(page: ft.Page):
    page.title = "JudgeMeNot"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # --- WINDOW SETTINGS ---
    page.padding = 0 
    page.window.min_width = 500
    page.window.min_height = 700
    page.window.width = 1200
    page.window.height = 800
    
    auth_service = AuthService()
    
    def route_change(route):
        # ---------------------------------------------------------
        # 🔒 ANDROID LOCK (DEPLOYMENT MODE)
        # ---------------------------------------------------------
        user_agent = page.client_user_agent or ""
        is_android = "Android" in user_agent or page.platform == ft.PagePlatform.ANDROID

        if is_android:
            if not page.route.startswith("/leaderboard"):
                page.go("/leaderboard")
                return 

        page.views.clear()
        uid = page.session.get("user_id")
        role = page.session.get("user_role")

        if page.route == "/login":
            page.views.append(ft.View("/login", [LoginView(page, on_login_success)], padding=0))
        
        elif page.route == "/signup":
            page.views.append(ft.View("/signup", [SignupView(page)], padding=0))
        
        elif page.route == "/admin" and role in ["Admin", "AdminViewer"]:
            page.views.append(ft.View("/admin", [AdminDashboardView(page, on_logout)], padding=0))
        
        elif page.route.startswith("/admin/event/") and role in ["Admin", "AdminViewer"]:
            eid = int(page.route.split("/")[-1])
            page.views.append(ft.View(f"/admin/event/{eid}", [AdminConfigView(page, eid)], padding=0))
        
        elif page.route == "/judge" and role == "Judge":
            page.views.append(ft.View("/judge", [JudgeView(page, on_logout)], padding=0))
        elif page.route == "/tabulator" and role == "Tabulator":
            page.views.append(ft.View("/tabulator", [TabulatorView(page, on_logout)], padding=0))
        
        elif page.route == "/leaderboard":
            page.views.append(ft.View("/leaderboard", [EventListView(page)], padding=0))
        elif page.route.startswith("/leaderboard/"):
            eid = int(page.route.split("/")[-1])
            page.views.append(ft.View(f"/leaderboard/{eid}", [EventLeaderboardView(page, eid)], padding=0))
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
        
        if user.role in ["Admin", "AdminViewer"]:
            page.go("/admin")
        else:
            page.go(f"/{user.role.lower()}")

    def on_logout(e):
        # --- NEW: LOG THE LOGOUT EVENT ---
        uid = page.session.get("user_id")
        if uid:
            auth_service.logout(uid)
        # ---------------------------------
        
        page.session.clear()
        page.go("/login")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/login")

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
    # my_ip = "192.168.43.175"
    my_ip = get_local_ip()
    port = 8550
    print(f"--------------------------------------------------")
    print(f"🚀  JUDGE ME NOT SYSTEM IS RUNNING!")
    print(f"📱  Judges connect here: http://{my_ip}:{port}")
    print(f"--------------------------------------------------")

    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host=my_ip)
    # ft.app(target=main)