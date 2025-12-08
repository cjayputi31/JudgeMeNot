import flet as ft
from services.quiz_service import QuizService
from core.database import SessionLocal
from models.all_models import Segment

def QuizConfigView(page: ft.Page, event_id: int):
    quiz_service = QuizService()

    q_round_name = ft.TextField(label="Round Name", width=280)
    q_points = ft.TextField(label="Points", width=280)
    q_total_qs = ft.TextField(label="Total Qs", width=280)
    
    main_column = ft.Column(spacing=20, scroll="adaptive", expand=True)

    def refresh_view():
        main_column.controls.clear()
        
        db = SessionLocal()
        rounds = db.query(Segment).filter(Segment.event_id == event_id).all()
        
        main_column.controls.append(
            ft.Row([
                ft.Text("Quiz Bee Configuration", size=24, weight="bold"),
                ft.ElevatedButton("Add Round", icon=ft.Icons.ADD, on_click=lambda e: page.open(round_dialog))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        for r in rounds:
            card = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Row([
                        ft.Column([
                            ft.Text(f"{r.name}", size=18, weight="bold"),
                            ft.Text(f"{r.total_questions} Questions"),
                        ]),
                        ft.Chip(label=ft.Text(f"{int(r.points_per_question)} pts/question"), bgcolor=ft.Colors.GREEN_100),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            main_column.controls.append(card)
        
        db.close()
        page.update()

    def save_round(e):
        try:
            pts = float(q_points.value)
            qs = int(q_total_qs.value)
            success, msg = quiz_service.add_round(event_id, q_round_name.value, pts, qs, 1)
            if success:
                page.open(ft.SnackBar(ft.Text("Round Added!"), bgcolor="green"))
                page.close(round_dialog)
                q_round_name.value = ""
                refresh_view()
            else:
                page.open(ft.SnackBar(ft.Text(f"Error: {msg}"), bgcolor="red"))
        except:
             page.open(ft.SnackBar(ft.Text("Invalid Input"), bgcolor="red"))

    round_dialog = ft.AlertDialog(
        title=ft.Text("Add Round"),
        content=ft.Column([q_round_name, q_points, q_total_qs], height=220, width=300, tight=True),
        actions=[ft.TextButton("Save", on_click=lambda e: save_round(e))]
    )
    
    refresh_view()
    return ft.Container(content=main_column, padding=20)