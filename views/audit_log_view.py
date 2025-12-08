import flet as ft
import threading
import time
from services.admin_service import AdminService

def AuditLogView(page: ft.Page, on_back_click=None):
    admin_service = AdminService()
    # State for polling
    is_active = True
    
    # UI Components
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID"), numeric=True),
            ft.DataColumn(ft.Text("User (Role)")),
            ft.DataColumn(ft.Text("Action")),
            ft.DataColumn(ft.Text("Details")),
            ft.DataColumn(ft.Text("Timestamp")),
        ],
        rows=[],
        border=ft.border.all(1, "grey"),
        vertical_lines=ft.border.BorderSide(1, "grey"),
        horizontal_lines=ft.border.BorderSide(1, "grey"),
        heading_row_color=ft.Colors.BLUE_50
    )

    last_updated_text = ft.Text("Loading...", size=12, color="grey", italic=True)

    def fetch_logs():
        """Fetches logs from DB and updates the table rows"""
        try:
            logs = admin_service.get_security_logs()
            new_rows = []
            for log in logs:
                ts_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                # Color code specific actions
                action_color = ft.Colors.BLACK
                if "LOGIN" in log.action: action_color = ft.Colors.BLUE
                elif "DELETE" in log.action: action_color = ft.Colors.RED
                elif "SCORE" in log.action: action_color = ft.Colors.GREEN
                elif "CREATE" in log.action: action_color = ft.Colors.PURPLE

                # Handle potentially missing user (if deleted)
                user_display = "Unknown"
                if log.user:
                    user_display = f"{log.user.username} ({log.user.role})"
                else:
                    user_display = f"User ID: {log.user_id} (Deleted)"

                new_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(log.id))),
                        ft.DataCell(ft.Text(user_display)),
                        ft.DataCell(ft.Text(log.action, color=action_color, weight="bold")),
                        ft.DataCell(ft.Text(log.details, size=12)),
                        ft.DataCell(ft.Text(ts_str, size=12)),
                    ])
                )
            
            data_table.rows = new_rows
            now_str = time.strftime("%H:%M:%S")
            last_updated_text.value = f"Auto-updated at: {now_str}"
            page.update()
        except Exception as e:
            print(f"Error fetching logs: {e}")

    def poll_logs():
        """Background thread to refresh logs every 3 seconds"""
        while is_active:
            fetch_logs()
            time.sleep(3)

    # Start Polling
    threading.Thread(target=poll_logs, daemon=True).start()

    # Cleanup when leaving
    def stop_polling(e):
        nonlocal is_active
        is_active = False
        if on_back_click:
            on_back_click(e)

    # Header Construction
    header_row = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_size=30, on_click=stop_polling), # Use stop_polling wrapper
            ft.Column([
                ft.Text("Security Audit Logs", size=24, weight="bold"),
                last_updated_text
            ], spacing=2)
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    # Return Layout
    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            controls=[
                header_row,
                ft.Divider(),
                # Scrollable area for the table
                ft.Column(
                    controls=[data_table],
                    expand=True,
                    )
            ],
            expand=True
            ),
    )