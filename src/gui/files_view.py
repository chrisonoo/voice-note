import customtkinter as ctk
import os
from src import config

class FilesView(ctk.CTkFrame):
    """
    GUI component that displays a list of user-selected files.
    Replaces the standard ttk.Treeview with a CTkScrollableFrame
    containing checkboxes and labels for a modern appearance.
    """
    def __init__(self, parent, title="Wczytane", **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=title, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # --- Scrollable Frame for File List ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scrollable_frame.grid_columnconfigure(1, weight=1) # Allow filename to expand

        # --- Header ---
        header_checkbox = ctk.CTkLabel(self.scrollable_frame, text="", width=40)
        header_checkbox.grid(row=0, column=0, padx=(5,0), pady=2)

        header_filename = ctk.CTkLabel(self.scrollable_frame, text="Nazwa", anchor="w")
        header_filename.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        header_duration = ctk.CTkLabel(self.scrollable_frame, text="Czas", width=75, anchor="center")
        header_duration.grid(row=0, column=2, padx=5, pady=2)

        # --- Data Storage ---
        self.file_widgets = [] # List to store refs to (checkbox, file_path, duration_sec)

    def populate_files(self, files_data):
        """
        Populates the scrollable frame with a list of files and their data.

        Args:
            files_data (list): A list of tuples, where each tuple contains
                               (file_path, duration_in_seconds).
        """
        self.clear_view()
        for i, (file_path, duration_sec) in enumerate(files_data, start=1):
            filename = os.path.basename(file_path)
            duration_str = f"{int(duration_sec // 60):02d}:{int(duration_sec % 60):02d}"
            is_long = duration_sec > config.MAX_FILE_DURATION_SECONDS

            # --- Checkbox ---
            checkbox = ctk.CTkCheckBox(self.scrollable_frame, text="")
            checkbox.grid(row=i, column=0, padx=(5,0), pady=2)
            if not is_long:
                checkbox.select()

            # --- Filename Label ---
            filename_label = ctk.CTkLabel(self.scrollable_frame, text=filename, anchor="w")
            filename_label.grid(row=i, column=1, sticky="ew", padx=5, pady=2)

            # --- Duration Label ---
            duration_label = ctk.CTkLabel(self.scrollable_frame, text=duration_str, anchor="center")
            duration_label.grid(row=i, column=2, padx=5, pady=2)

            if is_long:
                # Apply a visual cue for long files
                filename_label.configure(text_color="red")
                duration_label.configure(text_color="red")

            self.file_widgets.append((checkbox, file_path, duration_sec))

    def get_checked_files(self):
        """
        Returns a list of full paths to the files that are currently checked.
        """
        checked_files = []
        for checkbox, file_path, _ in self.file_widgets:
            if checkbox.get() == 1: # 1 means checked
                checked_files.append(file_path)
        return checked_files

    def clear_view(self):
        """
        Clears the view by destroying all file entry widgets and resetting the data list.
        """
        for widget_tuple in self.file_widgets:
            # Each tuple contains (checkbox, file_path, duration_sec)
            # but we only need to destroy the GUI elements (checkbox, labels)
            # The file_path and duration are just data.
            # Let's destroy all widgets in the scrollable_frame except the headers
            for widget in self.scrollable_frame.winfo_children():
                # Don't destroy the headers
                if widget.grid_info()["row"] > 0:
                    widget.destroy()

        self.file_widgets.clear()