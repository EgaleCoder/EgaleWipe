import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from cleaner import scan_all_folders
from worker import CleanerWorker

APP_NAME = "Egale Wipe"
COMPANY_NAME = "EgaleCoders"
# Default target folders dynamically resolved for the active Windows user
_local_appdata = os.environ.get("LOCALAPPDATA")
_windir = os.environ.get("WINDIR", r"C:\Windows")

DEFAULT_TARGETS = [
    Path(_local_appdata) / "Temp" if _local_appdata else Path.home() / "AppData" / "Local" / "Temp",
    Path(_windir) / "Temp",
]

# Robust asset path resolution for both dev environment and PyInstaller --onefile bundles
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

ASSETS_DIR = BASE_DIR / "assets"

# Header Logo (Center)
APP_LOGO_HEADER = ASSETS_DIR / "EgaleWipe_header.png"

# Window / Taskbar App Icon (from EgaleWipe.png)
WINDOW_ICON_ICO = ASSETS_DIR / "EgaleWipe.ico"
WINDOW_ICON_PNG = ASSETS_DIR / "app_icon.png"

# Company Assets (Bottom-Left footer)
COMPANY_LOGO_22 = ASSETS_DIR / "company_logo_22.png"


class ProgressDialog(tk.Toplevel):
    """
    Modal progress dialog that displays real-time deletion progress,
    current file path, counter, percentage, and a Cancel button.
    """

    def __init__(self, parent: tk.Tk, on_cancel_callback):
        super().__init__(parent)
        self.parent = parent
        self.on_cancel_callback = on_cancel_callback
        self.is_cancelled = False

        self.title("Cleaning...")
        self.geometry("460x200")
        self.resizable(False, False)
        self.configure(bg="#ffffff")
        self.transient(parent)
        self.grab_set()

        self._set_icon()
        self._build_ui()
        self._center_on_parent()

        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _set_icon(self):
        try:
            if WINDOW_ICON_ICO.exists():
                self.iconbitmap(str(WINDOW_ICON_ICO))
        except Exception:
            pass

    def _center_on_parent(self):
        self.update_idletasks()
        p_x = self.parent.winfo_x()
        p_y = self.parent.winfo_y()
        p_w = self.parent.winfo_width()
        p_h = self.parent.winfo_height()

        w = self.winfo_width()
        h = self.winfo_height()

        x = p_x + (p_w - w) // 2
        y = p_y + (p_h - h) // 2
        self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        content = tk.Frame(self, bg="#ffffff", padx=24, pady=18)
        content.pack(fill="both", expand=True)

        # Header Title
        self.lbl_title = tk.Label(
            content,
            text="Cleaning selected folders, please wait...",
            font=("Segoe UI", 10, "normal"),
            fg="#1e293b",
            bg="#ffffff",
            anchor="w",
        )
        self.lbl_title.pack(fill="x", pady=(0, 12))

        # Modern Green Progressbar Style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#e2e8f0",
            background="#22c55e",
            darkcolor="#16a34a",
            lightcolor="#4ade80",
            bordercolor="#cbd5e1",
            thickness=14,
        )

        self.progress_bar = ttk.Progressbar(
            content,
            orient="horizontal",
            mode="determinate",
            style="Green.Horizontal.TProgressbar",
            maximum=100,
            value=0,
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # Current File Label
        self.lbl_current_file = tk.Label(
            content,
            text="Preparing deletion...",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#ffffff",
            anchor="w",
            justify="left",
            wraplength=410,
        )
        self.lbl_current_file.pack(fill="x")

        # Stats Row (Items cleaned & percentage)
        stats_frame = tk.Frame(content, bg="#ffffff")
        stats_frame.pack(fill="x", pady=(6, 12))

        self.lbl_stats = tk.Label(
            stats_frame,
            text="0 items cleaned",
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#ffffff",
            anchor="w",
        )
        self.lbl_stats.pack(side="left")

        self.lbl_percent = tk.Label(
            stats_frame,
            text="0%",
            font=("Segoe UI", 9),
            fg="#334155",
            bg="#ffffff",
            anchor="e",
        )
        self.lbl_percent.pack(side="right")

        # Cancel Button
        btn_frame = tk.Frame(content, bg="#ffffff")
        btn_frame.pack(fill="x", side="bottom")

        self.btn_cancel = tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_cancel,
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#334155",
            activebackground="#f1f5f9",
            activeforeground="#1e293b",
            relief="solid",
            bd=1,
            padx=18,
            pady=4,
            cursor="hand2",
        )
        self.btn_cancel.pack(side="right")

    def update_progress(self, current_path: str, cleaned_count: int, total_items: int):
        if total_items > 0:
            pct = min(100, int((cleaned_count / total_items) * 100))
            self.progress_bar["value"] = pct
            self.lbl_percent.config(text=f"{pct}%")
        else:
            self.progress_bar["mode"] = "indeterminate"
            self.progress_bar.start(15)
            self.lbl_percent.config(text="...")

        # Format current path with ellipsis if very long
        display_path = current_path
        if len(display_path) > 55:
            display_path = "..." + display_path[-52:]

        self.lbl_current_file.config(text=display_path)
        self.lbl_stats.config(text=f"{cleaned_count} items cleaned")

    def _on_cancel(self):
        self.is_cancelled = True
        self.btn_cancel.config(state="disabled", text="Cancelling...")
        self.lbl_title.config(text="Stopping cleanup, please wait...")
        if self.on_cancel_callback:
            self.on_cancel_callback()

    def _on_window_close(self):
        if not self.is_cancelled:
            self._on_cancel()


class CheckboxRow:
    """
    Interactive row with a vector checkmark box (✓), folder icon, path label,
    and optional remove button for temporary paths.
    """

    def __init__(
        self,
        parent: tk.Widget,
        folder: Path,
        is_checked: bool = True,
        is_temporary: bool = False,
        on_remove_callback=None,
    ):
        self.folder = folder
        self.var = tk.BooleanVar(value=is_checked)
        self.is_temporary = is_temporary
        self.on_remove_callback = on_remove_callback

        self.frame = tk.Frame(parent, bg="#ffffff", cursor="hand2")
        self.frame.pack(fill="x", pady=4)

        # Custom Checkmark Canvas Box (20x20)
        self.canvas = tk.Canvas(
            self.frame,
            width=20,
            height=20,
            bg="#ffffff",
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack(side="left", padx=(0, 10))

        # Folder Icon
        self.lbl_folder_icon = tk.Label(
            self.frame,
            text="📁",
            font=("Segoe UI Emoji", 12),
            fg="#f59e0b",
            bg="#ffffff",
            cursor="hand2",
        )
        self.lbl_folder_icon.pack(side="left", padx=(0, 8))

        # Path Label
        self.lbl_path = tk.Label(
            self.frame,
            text=str(folder),
            font=("Segoe UI", 10),
            fg="#1e293b",
            bg="#ffffff",
            anchor="w",
            cursor="hand2",
        )
        self.lbl_path.pack(side="left", fill="x", expand=True)

        # Optional Remove Button for Temporary Folders
        if self.is_temporary and self.on_remove_callback:
            self.btn_remove = tk.Button(
                self.frame,
                text="✕",
                font=("Segoe UI", 9, "bold"),
                fg="#94a3b8",
                bg="#ffffff",
                activeforeground="#ef4444",
                activebackground="#fee2e2",
                relief="flat",
                bd=0,
                padx=6,
                pady=1,
                cursor="hand2",
                command=lambda: self.on_remove_callback(self),
            )
            self.btn_remove.pack(side="right", padx=(6, 0))
            self.btn_remove.bind("<Enter>", lambda e: self.btn_remove.config(fg="#ef4444", bg="#fee2e2"))
            self.btn_remove.bind("<Leave>", lambda e: self.btn_remove.config(fg="#94a3b8", bg="#ffffff"))

        # Bind clicks on sub-elements to toggle checkbox
        for widget in (self.frame, self.canvas, self.lbl_folder_icon, self.lbl_path):
            widget.bind("<Button-1>", lambda e: self.toggle())

        self.redraw()

    def toggle(self):
        self.var.set(not self.var.get())
        self.redraw()

    def set_checked(self, checked: bool):
        self.var.set(checked)
        self.redraw()

    def get_checked(self) -> bool:
        return self.var.get()

    def destroy(self):
        self.frame.destroy()

    def redraw(self):
        self.canvas.delete("all")
        if self.var.get():
            # Checked: Vibrant blue rounded box with white checkmark (✓)
            self.canvas.create_rectangle(
                1, 1, 19, 19,
                fill="#0284c7",
                outline="#0284c7",
                width=1,
            )
            # Vector checkmark lines (✓)
            self.canvas.create_line(4, 10, 8, 14, fill="#ffffff", width=2, capstyle="round")
            self.canvas.create_line(8, 14, 15, 6, fill="#ffffff", width=2, capstyle="round")
        else:
            # Unchecked: White box with soft gray border
            self.canvas.create_rectangle(
                1, 1, 19, 19,
                fill="#ffffff",
                outline="#94a3b8",
                width=1,
            )


class FolderCleanerApp:
    """
    Main Application Window for Egale Wipe.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("660x490")
        self.root.minsize(600, 460)
        self.root.configure(bg="#f8fafc")

        self.app_logo_img = None
        self.company_logo_img = None
        self.targets = DEFAULT_TARGETS
        self.checkbox_rows = []
        self.worker = None
        self.progress_dialog = None
        self._placeholder_text = "Enter or browse optional folder path..."

        self._load_assets()
        self._set_window_icons()
        self._build_ui()
        self._center_window()

    def _load_assets(self):
        # Load App Logo (centered header - prominent and crisp)
        try:
            if APP_LOGO_HEADER.exists():
                self.app_logo_img = tk.PhotoImage(file=str(APP_LOGO_HEADER))
        except Exception:
            pass

        # Load Company Logo (bottom-left footer)
        try:
            if COMPANY_LOGO_22.exists():
                self.company_logo_img = tk.PhotoImage(file=str(COMPANY_LOGO_22))
        except Exception:
            pass

    def _set_window_icons(self):
        try:
            if WINDOW_ICON_ICO.exists():
                self.root.iconbitmap(str(WINDOW_ICON_ICO))
        except Exception:
            pass

        try:
            if WINDOW_ICON_PNG.exists():
                raw_icon = tk.PhotoImage(file=str(WINDOW_ICON_PNG))
                self.root.iconphoto(False, raw_icon)
        except Exception:
            pass

    def _center_window(self):
        self.root.update_idletasks()
        w = 660
        h = 490
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # Main Outer Container
        main_container = tk.Frame(self.root, bg="#f8fafc", padx=32, pady=16)
        main_container.pack(fill="both", expand=True)

        # 1. Centered Header (App Logo + App Name + Short Description)
        header_frame = tk.Frame(main_container, bg="#f8fafc")
        header_frame.pack(fill="x", pady=(0, 10))

        if self.app_logo_img:
            lbl_app_logo = tk.Label(
                header_frame,
                image=self.app_logo_img,
                bg="#f8fafc",
            )
            lbl_app_logo.pack(pady=(0, 2))

        lbl_app_name = tk.Label(
            header_frame,
            text=APP_NAME,
            font=("Segoe UI", 18, "bold"),
            fg="#0f172a",
            bg="#f8fafc",
        )
        lbl_app_name.pack(pady=(0, 2))

        lbl_description = tk.Label(
            header_frame,
            text="Select the folders you want to clean with one click.",
            font=("Segoe UI", 10),
            fg="#64748b",
            bg="#f8fafc",
        )
        lbl_description.pack()

        # 2. Bordered Card Container
        card_border = tk.Frame(
            main_container,
            bg="#e2e8f0",
            padx=1,
            pady=1,
        )
        card_border.pack(fill="both", expand=True, pady=(0, 14))

        card_content = tk.Frame(card_border, bg="#ffffff", padx=16, pady=12)
        card_content.pack(fill="both", expand=True)

        # 2A. Optional Folder Input Section (Top of permanent folders)
        input_frame = tk.Frame(card_content, bg="#ffffff")
        input_frame.pack(fill="x", pady=(0, 8))

        self.entry_path_var = tk.StringVar()
        self.entry_path = tk.Entry(
            input_frame,
            textvariable=self.entry_path_var,
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#f8fafc",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor="#0284c7",
            highlightbackground="#cbd5e1",
        )
        self.entry_path.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        self.entry_path.bind("<Return>", lambda e: self._on_add_custom_path())

        # Placeholder setup
        self._set_entry_placeholder(self._placeholder_text)

        # Browse Button
        self.btn_browse = tk.Button(
            input_frame,
            text="Browse",
            command=self._on_browse_clicked,
            font=("Segoe UI", 9),
            bg="#f1f5f9",
            fg="#334155",
            activebackground="#e2e8f0",
            activeforeground="#1e293b",
            relief="solid",
            bd=1,
            padx=14,
            pady=3,
            cursor="hand2",
        )
        self.btn_browse.pack(side="left", padx=(0, 6))

        # OK / Add Button
        self.btn_ok = tk.Button(
            input_frame,
            text="OK",
            command=self._on_add_custom_path,
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief="flat",
            padx=16,
            pady=4,
            cursor="hand2",
        )
        self.btn_ok.pack(side="left")

        # Hover effects for input buttons
        self._apply_hover(self.btn_browse, bg_default="#f1f5f9", bg_hover="#e2e8f0")
        self._apply_hover(self.btn_ok, bg_default="#0284c7", bg_hover="#0369a1")

        # Separator line between input and folder checklist
        sep = tk.Frame(card_content, bg="#e2e8f0", height=1)
        sep.pack(fill="x", pady=(2, 8))

        # 2B. Folders List Container
        self.folders_container = tk.Frame(card_content, bg="#ffffff")
        self.folders_container.pack(fill="both", expand=True)

        # Build Permanent Checkbox Rows
        for folder in self.targets:
            row = CheckboxRow(
                self.folders_container,
                folder,
                is_checked=True,
                is_temporary=False,
            )
            self.checkbox_rows.append(row)

        # 3. Bottom Controls (Company Logo Footer & Action Buttons)
        bottom_frame = tk.Frame(main_container, bg="#f8fafc")
        bottom_frame.pack(fill="x", side="bottom")

        # Bottom Left: Company Logo + Created by text
        company_footer = tk.Frame(bottom_frame, bg="#f8fafc")
        company_footer.pack(side="left", anchor="center")

        if self.company_logo_img:
            lbl_company_logo = tk.Label(
                company_footer,
                image=self.company_logo_img,
                bg="#f8fafc",
            )
            lbl_company_logo.pack(side="left", padx=(0, 6))

        lbl_created_by = tk.Label(
            company_footer,
            text=f"Created by :- {COMPANY_NAME}, 2026",
            font=("Segoe UI", 9),
            fg="#64748b",
            bg="#f8fafc",
        )
        lbl_created_by.pack(side="left")

        # Bottom Right: Back and Clean Buttons
        actions_frame = tk.Frame(bottom_frame, bg="#f8fafc")
        actions_frame.pack(side="right")

        # Back Button
        self.btn_back = tk.Button(
            actions_frame,
            text="Back",
            command=self._on_back_clicked,
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#334155",
            activebackground="#f1f5f9",
            activeforeground="#1e293b",
            relief="solid",
            bd=1,
            padx=22,
            pady=6,
            cursor="hand2",
        )
        self.btn_back.pack(side="left", padx=(0, 12))

        # Clean Button
        self.btn_clean = tk.Button(
            actions_frame,
            text="Clean",
            command=self._on_clean_clicked,
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#0284c7",
            activebackground="#f0f9ff",
            activeforeground="#0369a1",
            relief="solid",
            bd=1,
            highlightcolor="#0284c7",
            padx=24,
            pady=6,
            cursor="hand2",
        )
        self.btn_clean.pack(side="left")

        # Interactive Button Hover Effects
        self._apply_hover(self.btn_back, bg_default="#ffffff", bg_hover="#f1f5f9")
        self._apply_hover(self.btn_clean, bg_default="#ffffff", bg_hover="#f0f9ff")

    def _set_entry_placeholder(self, text: str):
        self._placeholder_text = text
        self.entry_path_var.set(text)
        self.entry_path.config(fg="#94a3b8")
        self.entry_path.bind("<FocusIn>", self._on_entry_focus_in)
        self.entry_path.bind("<FocusOut>", self._on_entry_focus_out)

    def _on_entry_focus_in(self, event=None):
        if self.entry_path_var.get() == self._placeholder_text:
            self.entry_path_var.set("")
            self.entry_path.config(fg="#1e293b")

    def _on_entry_focus_out(self, event=None):
        if not self.entry_path_var.get().strip():
            self.entry_path_var.set(self._placeholder_text)
            self.entry_path.config(fg="#94a3b8")

    def _on_browse_clicked(self):
        folder_selected = filedialog.askdirectory(
            title="Select Folder to Clean",
            parent=self.root,
        )
        if folder_selected:
            norm_path = os.path.normpath(folder_selected)
            self.entry_path.config(fg="#1e293b")
            self.entry_path_var.set(norm_path)
            self.entry_path.focus_set()

    def _on_add_custom_path(self):
        raw_val = self.entry_path_var.get().strip()
        if not raw_val or raw_val == self._placeholder_text:
            messagebox.showinfo(
                APP_NAME,
                "Please enter or browse a valid folder path.",
                parent=self.root,
            )
            return

        target_path = Path(raw_val).resolve()

        # Check if already in checklist
        for row in self.checkbox_rows:
            if row.folder == target_path:
                row.set_checked(True)
                self.entry_path_var.set(self._placeholder_text)
                self.entry_path.config(fg="#94a3b8")
                self.root.focus_set()
                return

        # Add as new temporary row
        new_row = CheckboxRow(
            self.folders_container,
            target_path,
            is_checked=True,
            is_temporary=True,
            on_remove_callback=self._remove_custom_row,
        )
        self.checkbox_rows.append(new_row)

        # Reset entry field placeholder
        self.entry_path_var.set(self._placeholder_text)
        self.entry_path.config(fg="#94a3b8")
        self.root.focus_set()

    def _remove_custom_row(self, row: CheckboxRow):
        if row in self.checkbox_rows:
            self.checkbox_rows.remove(row)
            row.destroy()

    def _apply_hover(self, button: tk.Button, bg_default: str, bg_hover: str):
        button.bind("<Enter>", lambda e: button.configure(bg=bg_hover))
        button.bind("<Leave>", lambda e: button.configure(bg=bg_default))

    def _on_back_clicked(self):
        """Action when Back button is pressed (toggles all checkboxes)."""
        all_checked = all(row.get_checked() for row in self.checkbox_rows)
        new_state = not all_checked
        for row in self.checkbox_rows:
            row.set_checked(new_state)

    def _on_clean_clicked(self):
        """Validates selection and launches cleanup thread with progress dialog."""
        selected_folders = [row.folder for row in self.checkbox_rows if row.get_checked()]

        if not selected_folders:
            messagebox.showwarning(
                APP_NAME,
                "Please select at least one folder to clean.",
            )
            return

        # Ensure target folders exist on disk
        for folder in selected_folders:
            folder.mkdir(parents=True, exist_ok=True)

        # Open Progress Modal
        self.progress_dialog = ProgressDialog(self.root, on_cancel_callback=self._cancel_worker)

        # Initialize Background Worker
        self.worker = CleanerWorker(
            folders=selected_folders,
            on_progress=self._handle_progress,
            on_prompt_skip=self._handle_prompt_skip,
            on_complete=self._handle_complete,
            on_error=self._handle_error,
            post_to_ui=lambda fn: self.root.after(0, fn),
        )
        self.worker.start()

    def _cancel_worker(self):
        if self.worker:
            self.worker.cancel()

    def _handle_progress(self, current_path: str, cleaned_count: int, total_items: int):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.progress_dialog.update_progress(current_path, cleaned_count, total_items)

    def _handle_prompt_skip(self, file_name: str, error_msg: str) -> bool:
        """
        Native Windows popup asking whether to skip an in-use / locked file.
        """
        message = (
            f'The file "{file_name}" is in use and cannot be deleted.\n\n'
            f"Do you want to skip this file and continue?"
        )
        return messagebox.askyesno(
            title=APP_NAME,
            message=message,
            icon="warning",
            parent=self.progress_dialog if self.progress_dialog and self.progress_dialog.winfo_exists() else self.root,
        )

    def _handle_complete(self, summary: dict):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.progress_dialog.destroy()
            self.progress_dialog = None

        # Remove all temporary folder rows from UI and checklist after cleaning
        temp_rows = [row for row in self.checkbox_rows if row.is_temporary]
        for row in temp_rows:
            self._remove_custom_row(row)

        # Ensure permanent rows remain active and checked
        for row in self.checkbox_rows:
            if not row.is_temporary:
                row.set_checked(True)

        if summary.get("cancelled", False):
            messagebox.showinfo(
                APP_NAME,
                f"Cleaning was cancelled.\n\n"
                f"Items deleted: {summary.get('cleaned_count', 0)}\n"
                f"Items skipped: {summary.get('skipped_count', 0)}",
            )
        else:
            total_cleaned = summary.get("cleaned_count", 0)
            cleaned_folders = summary.get("cleaned_folders", [])
            folder_list_str = "\n".join(f"• {f}" for f in cleaned_folders)

            messagebox.showinfo(
                APP_NAME,
                f"Cleanup completed successfully!\n\n"
                f"Total items deleted: {total_cleaned}\n\n"
                f"Cleaned folders:\n{folder_list_str}",
            )

    def _handle_error(self, error: Exception):
        if self.progress_dialog and self.progress_dialog.winfo_exists():
            self.progress_dialog.destroy()
            self.progress_dialog = None

        messagebox.showerror(
            APP_NAME,
            f"An unexpected error occurred during cleaning:\n\n{error}",
        )


def main():
    root = tk.Tk()
    app = FolderCleanerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
