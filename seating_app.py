import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from main import SeatingGenerator, find_optimal_configuration, visualize_seating, calculate_arrangement_score


class SeatingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wedding Seating Arranger")

        self.guests = []
        self.constraints = []
        self.current_arrangement = 0
        self.arrangements = []

        self.create_widgets()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Input Section
        input_frame = ttk.LabelFrame(main_frame, text="Guest Setup")
        input_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Guest Entry
        ttk.Label(input_frame, text="Guests (comma-separated):").grid(row=0, column=0)
        self.guest_entry = ttk.Entry(input_frame, width=40)
        self.guest_entry.grid(row=0, column=1, padx=5)

        # Constraints List
        ttk.Label(input_frame, text="Constraints:").grid(row=1, column=0)
        self.constraints_list = tk.Listbox(input_frame, width=40, height=5)
        self.constraints_list.grid(row=1, column=1, padx=5, pady=5)

        # Constraint Controls
        constraint_btn_frame = ttk.Frame(input_frame)
        constraint_btn_frame.grid(row=2, column=1, sticky="w")
        ttk.Button(constraint_btn_frame, text="Add Constraint",
                   command=self.add_constraint_dialog).pack(side=tk.LEFT)

        # Configuration Section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration")
        config_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.table_mode = tk.StringVar(value="auto")
        ttk.Radiobutton(config_frame, text="Auto Table Sizes", variable=self.table_mode,
                        value="auto").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(config_frame, text="Manual Table Size", variable=self.table_mode,
                        value="manual").grid(row=1, column=0, sticky="w")

        self.min_size = tk.IntVar(value=5)
        self.max_size = tk.IntVar(value=10)
        ttk.Label(config_frame, text="Min Size:").grid(row=0, column=1)
        ttk.Entry(config_frame, textvariable=self.min_size, width=5).grid(row=0, column=2)
        ttk.Label(config_frame, text="Max Size:").grid(row=0, column=3)
        ttk.Entry(config_frame, textvariable=self.max_size, width=5).grid(row=0, column=4)

        self.fixed_size = tk.IntVar(value=8)
        ttk.Label(config_frame, text="Table Size:").grid(row=1, column=1)
        ttk.Entry(config_frame, textvariable=self.fixed_size, width=5).grid(row=1, column=2)

        # Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Generate", command=self.generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Next Arrangement",
                   command=self.next_arrangement).pack(side=tk.LEFT, padx=5)

        # Visualization Area
        self.fig_frame = ttk.Frame(main_frame)
        self.fig_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")

    def add_constraint_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Constraint")

        guests = self.guest_entry.get().split(',')
        if not guests:
            messagebox.showwarning("No Guests", "Please enter guests first")
            return

        ttk.Label(dialog, text="Guest 1:").grid(row=0, column=0)
        guest1 = ttk.Combobox(dialog, values=guests)
        guest1.grid(row=0, column=1)

        ttk.Label(dialog, text="Relation:").grid(row=1, column=0)
        relation = ttk.Combobox(dialog, values=["must", "must not", "prefer", "avoid"])
        relation.grid(row=1, column=1)

        ttk.Label(dialog, text="Guest 2:").grid(row=2, column=0)
        guest2 = ttk.Combobox(dialog, values=guests)
        guest2.grid(row=2, column=1)

        def save_constraint():
            g1 = guest1.get().strip()
            g2 = guest2.get().strip()
            rel = relation.get().strip()
            if g1 and g2 and rel:
                self.constraints.append((g1, g2, rel))
                self.constraints_list.insert(tk.END, f"{g1} {rel} {g2}")
                dialog.destroy()

        ttk.Button(dialog, text="Save", command=save_constraint).grid(row=3, columnspan=2)

    def generate(self):
        self.guests = [g.strip() for g in self.guest_entry.get().split(',') if g.strip()]

        if len(self.guests) < 2:
            messagebox.showerror("Error", "Please enter at least 2 guests")
            return

        constraints = []
        for constr in self.constraints:
            a, b, rel = constr
            rel_map = {
                "must": "must",
                "must not": "must_not",
                "prefer": "prefer",
                "avoid": "prefer_apart"
            }
            constraints.append((a, b, rel_map[rel]))

        if self.table_mode.get() == "auto":
            result, tsize, ntables, _ = find_optimal_configuration(
                len(self.guests), self.guests, constraints,
                self.min_size.get(), self.max_size.get()
            )
        else:
            tsize = self.fixed_size.get()
            ntables = (len(self.guests) + tsize - 1) // tsize
            generator = SeatingGenerator(self.guests, tsize, ntables, constraints)
            result = generator.generate_seating()

        if not result['tables']:
            messagebox.showerror("Error", result['message'])
            return

        self.arrangements = [(result['tables'], tsize, ntables)]
        self.current_arrangement = 0
        self.show_arrangement()

    def show_arrangement(self):
        for widget in self.fig_frame.winfo_children():
            widget.destroy()

        tables, tsize, ntables = self.arrangements[self.current_arrangement]
        fig = visualize_seating(tables)

        canvas = FigureCanvasTkAgg(fig, master=self.fig_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def next_arrangement(self):
        if self.current_arrangement < len(self.arrangements) - 1:
            self.current_arrangement += 1
            self.show_arrangement()


if __name__ == "__main__":
    root = tk.Tk()
    app = SeatingApp(root)
    root.mainloop()