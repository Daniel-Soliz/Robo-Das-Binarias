"""Tema desktop escuro em ttk (sem dependência externa ou alterar a lógica)."""
from tkinter import ttk

BG = "#08111f"
PANEL = "#101c2d"
PANEL_2 = "#15243a"
TEXT = "#e9f3ff"
MUTED = "#9bb0c6"
ACCENT = "#45c8ed"


def apply_theme(root):
    root.configure(background=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT, padding=4)
    style.configure("Title.TLabel", background=BG, foreground=TEXT,
                    font=("Segoe UI Semibold", 22))
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("TButton", padding=(13, 10), background=PANEL_2,
                    foreground=TEXT, borderwidth=0, relief="flat",
                    focuscolor=ACCENT)
    style.map("TButton", background=[
        ("disabled", "#19283b"), ("pressed", "#176482"), ("active", "#274764")],
        foreground=[("disabled", "#74889d"), ("active", "#ffffff")])
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(2, 2, 2, 0))
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                    padding=(15, 10), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", PANEL_2), ("active", "#20374e")],
              foreground=[("selected", "#f4fbff"), ("active", TEXT)])
    style.configure("TEntry", fieldbackground=PANEL_2, foreground=TEXT,
                    insertcolor=TEXT, bordercolor="#30465c", padding=5)
    style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2,
                    foreground=TEXT, arrowcolor=TEXT, bordercolor="#30465c",
                    selectbackground=PANEL_2, selectforeground=TEXT,
                    padding=(7, 6))
    style.map("TCombobox",
              fieldbackground=[("readonly", PANEL_2)],
              foreground=[("readonly", TEXT)],
              selectbackground=[("readonly", PANEL_2)],
              selectforeground=[("readonly", TEXT)])
    style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL_2)
    style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                    foreground=TEXT, rowheight=30, borderwidth=0)
    style.map("Treeview", background=[("selected", "#155c7b")])
    style.configure("Treeview.Heading", background=PANEL_2, foreground=TEXT,
                    font=("Segoe UI Semibold", 10), relief="flat")
    style.map("Treeview.Heading", background=[("active", "#274764")])
    return style
