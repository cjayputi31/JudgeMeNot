import flet as ft
from core.database import SessionLocal
from models.all_models import Event
# Import the decoupled views
from views.config.pageant_config_view import PageantConfigView
from views.config.quiz_config_view import QuizConfigView

def AdminConfigView(page: ft.Page, event_id: int):
    # 1. Fetch Event to determine type
    db = SessionLocal()
    event = db.query(Event).get(event_id)
    db.close()

    if not event:
        return ft.Container(content=ft.Text("Event not found!", color="red", size=20))

    # 2. Common Header (Optional, or handled inside views)
    header = ft.Container(
        padding=10,
        content=ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: page.go("/admin")),
            ft.Text(f"Event: {event.name}", size=24, weight="bold")
        ])
    )

    # 3. Route to specific View based on Type
    # Note: We pass the page and event_id so they can fetch their own data
    if event.event_type == "Pageant":
        content_view = PageantConfigView(page, event_id)
    else:
        content_view = QuizConfigView(page, event_id)

    # 4. Return assembled layout
    return ft.Column(
        controls=[
            header,
            ft.Divider(height=1),
            content_view # This is the full layout from the specific view
        ],
        expand=True
    )