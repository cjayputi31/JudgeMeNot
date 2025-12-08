import flet as ft
import threading
import time
from services.quiz_service import QuizService
from services.event_service import EventService
from core.database import SessionLocal
from models.all_models import Event, Segment

def ViewerDashboard(page: ft.Page, event_id: int):
    # Services
    quiz_service = QuizService()
    event_service = EventService()

    # State
    is_active = True
    
    # UI Elements
    title_text = ft.Text("Event Leaderboard", size=40, weight="bold", color="white")
    status_text = ft.Text("Waiting for updates...", color="white70", size=16)
    
    # The main grid for Top 3 and List for others
    top3_row = ft.Row(alignment="center", spacing=20)
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

        # 2. Determine "Mode" (Cumulative vs Final Round)
        # We look for the last created segment to see if it's a Final/Clincher
        last_segment = db.query(Segment).filter(Segment.event_id == event_id).order_by(Segment.order_index.desc()).first()
        
        scores = []
        mode_label = ""
        
        if last_segment and (last_segment.is_final or "Clincher" in last_segment.name or "Final" in last_segment.name):
            # It's a Final Round context. 
            # We must show scores specfic to this round for the participants in it.
            mode_label = f"ROUND: {last_segment.name.upper()}"
            scores = quiz_service.get_live_scores(event_id, specific_round_id=last_segment.id)
            
            # If we only have a few people in the final, we might want to also 
            # show the eliminated people below them based on previous rounds?
            # For simplicity, this view focuses on the active finalists.
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
        # We assume results are sorted by score DESC from the service
        # Assign explicit ranks handling ties is complex visually, 
        # so we trust the service order for now or simple index.
        
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
                    ft.Text(data['name'], size=18, weight="bold", color="white", text_align="center"),
                    ft.Container(
                        content=ft.Text(f"{data['total_score']}", size=30, weight="bold", color=color),
                        bgcolor="white", border_radius=10, padding=10
                    )
                ], horizontal_alignment="center", spacing=5),
                bgcolor=color,
                width=220,
                height=height, # Vary height for 1st, 2nd, 3rd
                border_radius=15,
                padding=20,
                shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.BLACK54)
            )

        # 2nd Place (Left)
        if len(top_3_data) >= 2:
            top3_row.controls.append(create_podium_card(2, top_3_data[1], ft.Colors.BLUE_GREY_400, 280, ft.Icons.SHIELD))
        
        # 1st Place (Center, Tallest)
        if len(top_3_data) >= 1:
            top3_row.controls.append(create_podium_card(1, top_3_data[0], ft.Colors.AMBER_600, 320, ft.Icons.EmojiEvents))
            
        # 3rd Place (Right)
        if len(top_3_data) >= 3:
            top3_row.controls.append(create_podium_card(3, top_3_data[2], ft.Colors.BROWN_400, 260, ft.Icons.SHIELD))

        # --- Render List for the rest ---
        for i, res in enumerate(others_data):
            rank = i + 4
            list_view.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(str(rank), weight="bold"),
                                width=40, height=40, bgcolor="white24", border_radius=20, alignment=ft.alignment.center
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
            time.sleep(3) # Update every 3 seconds

    # Start Polling
    threading.Thread(target=poll_updates, daemon=True).start()

    def go_back(e):
        nonlocal is_active
        is_active = False # Stop thread
        page.go("/") # Or wherever your home is

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
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=go_back, icon_color="white"),
                ft.Column([title_text, status_text], spacing=0)
            ]),
            ft.Divider(color="white24"),
            ft.Container(content=top3_row, padding=ft.padding.only(top=20, bottom=20)),
            ft.Text("Rankings", color="white70", weight="bold"),
            list_view
        ])
    )