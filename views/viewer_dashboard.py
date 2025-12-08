import flet as ft
import threading
import time
from services.quiz_service import QuizService
from core.database import SessionLocal
from models.all_models import Event, Segment

# ---------------------------------------------------------
# VIEW 1: EVENT GALLERY (List of All Events)
# ---------------------------------------------------------
def EventListView(page: ft.Page):
    
    # 1. Fetch All Events
    db = SessionLocal()
    events = db.query(Event).all()
    db.close()

    # --- SMART NAVIGATION LOGIC ---
    def go_back_logic(e):
        # Check who is currently logged in
        user_role = page.session.get("user_role")
        print(f"DEBUG: Back Button Clicked. Session Role: '{user_role}'") # Console Debug
        
        if user_role in ["Admin", "AdminViewer"]:
            page.go("/admin")
        elif user_role == "Judge":
            page.go("/judge")
        elif user_role == "Tabulator":
            page.go("/tabulator")
        else:
            # Public user or not logged in (Session might be expired)
            print("DEBUG: No active role found. Redirecting to Login.")
            page.go("/login")

    # 2. Card Builder
    def create_event_card(event_data):
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.EMOJI_EVENTS, size=40, color="white70"),
                ft.Text(event_data.name, size=18, weight="bold", color="white", text_align="center", no_wrap=False, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Container(
                    content=ft.Text("View Standings", size=12, color="white"),
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    bgcolor=ft.Colors.BLUE_600,
                    border_radius=20
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            bgcolor=ft.Colors.WHITE10,
            border_radius=15,
            padding=20,
            width=200,
            height=200,
            ink=True,
            on_click=lambda e: page.go(f"/leaderboard/{event_data.id}"),
            border=ft.border.all(1, ft.Colors.WHITE10),
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12)
        )

    # 3. Layout
    header = ft.Column([
        ft.Text("Event Gallery", size=32, weight="bold", color="white"),
        ft.Text("Select an event to view live results", size=16, color="white70")
    ])

    grid = ft.GridView(
        expand=True,
        runs_count=5,
        max_extent=250,
        child_aspect_ratio=1.0,
        spacing=20,
        run_spacing=20,
    )

    if not events:
        grid.controls.append(ft.Text("No events found.", color="white70"))
    else:
        for e in events:
            grid.controls.append(create_event_card(e))

    return ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[ft.Colors.BLUE_900, ft.Colors.PURPLE_900]
        ),
        padding=30,
        content=ft.Column([
            ft.Row([
                # Logic attached here
                ft.IconButton(ft.Icons.ARROW_BACK, icon_color="white", tooltip="Go Back", on_click=go_back_logic),
                header
            ], spacing=20),
            ft.Divider(color="white24", height=30),
            grid
        ])
    )

# ---------------------------------------------------------
# VIEW 2: SPECIFIC EVENT LEADERBOARD
# ---------------------------------------------------------
def EventLeaderboardView(page: ft.Page, event_id: int):
    # Services
    quiz_service = QuizService()

    # State
    is_active = True

    # UI Elements
    title_text = ft.Text("Loading...", size=30, weight="bold", color="white")
    status_text = ft.Text("Waiting for updates...", color="white70", size=14)

    # The main grid for Top 3 and List for others
    top3_row = ft.Row(alignment="center", spacing=20, wrap=True) # Wrap allows resizing on small screens
    list_view = ft.ListView(expand=True, spacing=10, padding=20)

    def get_final_scores():
        """
        Smart logic to determine which scores to show.
        If the last round is a 'Final' (Back-to-Zero), it prioritizes those scores.
        """
        db = SessionLocal()
        # 1. Get Event Details
        event = db.query(Event).get(event_id)
        if event:
            title_text.value = event.name
        else:
            title_text.value = "Event Not Found"

        # 2. Determine "Mode" (Cumulative vs Final Round)
        # We look for the last created segment to see if it's a Final/Clincher
        last_segment = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index.desc()).first()

        scores = []
        mode_label = ""

        if last_segment and (last_segment.is_final or "Clincher" in last_segment.name or "Final" in last_segment.name):
            # It's a Final Round context. 
            mode_label = f"ROUND: {last_segment.name.upper()}"
            scores = quiz_service.get_live_scores(event_id, specific_round_id=last_segment.id)

            # Filter for participants in this round
            if last_segment.participating_school_ids:
                p_ids = [int(x) for x in last_segment.participating_school_ids.split(",") if x.strip()]
                scores = [s for s in scores if s['contestant_id'] in p_ids]
        else:
            # Standard Cumulative
            mode_label = "OVERALL STANDINGS"
            scores = quiz_service.get_live_scores(event_id)

        db.close()
        return scores, mode_label

    def refresh_leaderboard():
        results, mode = get_final_scores()

        status_text.value = f"{mode} • Live Updates"
        top3_row.controls.clear()
        list_view.controls.clear()

        if not results:
            list_view.controls.append(ft.Text("No scores available yet.", color="white"))
            page.update()
            return

        # --- Render Top 3 (Podium) ---
        top_3_data = results[:3]
        others_data = results[3:]

        # Helper for Podium Card
        def create_podium_card(rank, data, color, height, icon):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, color="white", size=40),
                    ft.Text(f"Rank {rank}", color="white70", weight="bold"),
                    ft.CircleAvatar(
                        content=ft.Text(str(rank), size=20, weight="bold"),
                        bgcolor="white", color=color, radius=30
                    ),
                    ft.Text(data['name'], size=16, weight="bold", color="white", text_align="center", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Container(
                        content=ft.Text(f"{data['total_score']}", size=24, weight="bold", color=color),
                        bgcolor="white", border_radius=10, padding=10
                    )
                ], horizontal_alignment="center", spacing=5),
                bgcolor=color,
                width=200,
                height=height, 
                border_radius=15,
                padding=15,
                shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.BLACK54),
                animate_scale=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT)
            )

        # 2nd Place (Left)
        if len(top_3_data) >= 2:
            top3_row.controls.append(create_podium_card(2, top_3_data[1], ft.Colors.BLUE_GREY_400, 260, ft.Icons.SHIELD))

        # 1st Place (Center, Tallest)
        if len(top_3_data) >= 1:
            top3_row.controls.append(create_podium_card(1, top_3_data[0], ft.Colors.AMBER_600, 300, ft.Icons.EMOJI_EVENTS))

        # 3rd Place (Right)
        if len(top_3_data) >= 3:
            top3_row.controls.append(create_podium_card(3, top_3_data[2], ft.Colors.BROWN_400, 240, ft.Icons.SHIELD))

        # --- Render List for the rest ---
        for i, res in enumerate(others_data):
            rank = i + 4
            list_view.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(str(rank), weight="bold", color="black"),
                                width=40, height=40, bgcolor="white", border_radius=20, alignment=ft.alignment.center
                            ),
                            ft.Text(res['name'], size=16, weight="bold", color="white"),
                        ]),
                        ft.Text(f"{res['total_score']} pts", size=18, weight="bold", color="amber"),
                    ], alignment="spaceBetween"),
                    padding=15,
                    bgcolor="white10",
                    border_radius=10
                )
            )

        page.update()

    def poll_updates():
        while is_active:
            try:
                refresh_leaderboard()
            except:
                pass
            time.sleep(3) 

    # Start Polling
    threading.Thread(target=poll_updates, daemon=True).start()

    def go_back(e):
        nonlocal is_active
        is_active = False 
        page.go("/leaderboard") # Go back to the Gallery List

    # Layout
    return ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=[ft.Colors.BLUE_900, ft.Colors.PURPLE_900]
        ),
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back, icon_color="white", tooltip="Back to Gallery"),
                ft.Column([title_text, status_text], spacing=0)
            ]),
            ft.Divider(color="white24"),
            ft.Container(content=top3_row, padding=ft.padding.only(top=10, bottom=20)),
            ft.Text("Rankings", color="white70", weight="bold"),
            list_view
        ]))