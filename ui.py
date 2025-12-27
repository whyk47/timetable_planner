import tkinter as tk
from tkinter import messagebox, ttk

from load import process_all_courses
from planner import run_planner


class TimetableGUI:
    def __init__(self, top_results, courses_map):
        self.top_results = top_results
        self.courses_map = courses_map
        self.current_index = 0

        # Initialize Main Window
        self.root = tk.Tk()
        self.root.title("NTU Course Planner - Top 20 Desirable Schedules")
        self.root.geometry("1100x850")
        self.root.configure(bg="#f0f2f5")

        self.setup_ui()
        self.update_view()
        self.root.mainloop()

    def setup_ui(self):
        # Header Section
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(fill="x")

        self.title_label = tk.Label(
            header_frame,
            text="Rank #1",
            font=("Helvetica", 18, "bold"),
            fg="white",
            bg="#2c3e50",
            pady=10,
        )
        self.title_label.pack()

        # Score Info Section
        score_frame = tk.Frame(self.root, bg="#f0f2f5", pady=10)
        score_frame.pack(fill="x")

        self.score_label = tk.Label(
            score_frame, text="", font=("Helvetica", 12), bg="#f0f2f5"
        )
        self.score_label.pack()

        self.mods_label = tk.Label(
            score_frame, text="", font=("Helvetica", 11, "italic"), bg="#f0f2f5"
        )
        self.mods_label.pack()

        # Grid Section (Treeview for the Timetable)
        style = ttk.Style()
        style.configure("Treeview", rowheight=45, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

        self.tree_frame = tk.Frame(
            self.root, highlightbackground="black", highlightthickness=1
        )
        self.tree_frame.pack(expand=True, fill="both", padx=20, pady=10)

        columns = ("Time", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")

        self.tree.pack(expand=True, fill="both")

        # Navigation Buttons
        nav_frame = tk.Frame(self.root, bg="#f0f2f5", pady=20)
        nav_frame.pack(fill="x")

        tk.Button(
            nav_frame,
            text="◀ Previous",
            command=self.prev_sol,
            width=15,
            bg="#95a5a6",
            fg="white",
            font=("bold"),
        ).pack(side="left", padx=100)

        tk.Button(
            nav_frame,
            text="Next ▶",
            command=self.next_sol,
            width=15,
            bg="#3498db",
            fg="white",
            font=("bold"),
        ).pack(side="right", padx=100)

    def update_view(self):
        # Get data for current rank
        score, assignment = self.top_results[self.current_index]
        f_days, streak, morning_lessons = score

        # Update Labels
        self.title_label.config(text=f"Rank #{self.current_index + 1}")
        self.score_label.config(
            text=f"Score: {f_days} Free Days | Longest Streak: {streak} Days | Morning Blues: {-morning_lessons}"
        )
        self.mods_label.config(
            text="Indexes:\n" + ", ".join([f"{k}: {v}" for k, v in assignment])
        )

        # Clear and Rebuild Grid
        for i in self.tree.get_children():
            self.tree.delete(i)

        days = range(1, 8)
        time_slots = range(8, 19)

        for hour in time_slots:
            row_data = [f"{hour:02d}30"]
            for day in days:
                cell_text = ""
                # Find if any course is in this slot
                for code, idx in assignment:
                    for lesson in self.courses_map[code].indexes[idx]:
                        if (
                            lesson.day == day
                            and hour >= lesson.start
                            and hour < lesson.end
                        ):
                            cell_text = f"{code} ({lesson.lesson_type})"
                row_data.append(cell_text)
            self.tree.insert("", "end", values=row_data)

    def next_sol(self):
        if self.current_index < len(self.top_results) - 1:
            self.current_index += 1
            self.update_view()
        else:
            messagebox.showinfo("End", "This is the last of the top 20 schedules.")

    def prev_sol(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_view()


if __name__ == "__main__":
    # 1. Run your solver
    target_courses = [
        "AB1201",
        "AB1601",
        "SC2001",
        "SC2002",
        "AD1102",
        "CC0001",
        "SC1006",
        # "SC2203",
        # "AB2008",
        "BC2406",
    ]
    all_courses = process_all_courses("raw_data", target_courses=target_courses)
    target_num = 7
    result = run_planner(
        list(all_courses.values()),
        {"AB1201": "00182", "AB1601": "00871", "AD1102": "00109"},
        target_num,
    )

    # 2. Launch the Pop-up Window
    # results should be sorted: tracker.get_sorted_results()
    if result:
        TimetableGUI(result, all_courses)
    else:
        print("No valid timetable could be generated.")
