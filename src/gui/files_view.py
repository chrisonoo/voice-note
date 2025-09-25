import customtkinter as ctk
import os
from src import config
from .audio_player import AudioPlayer

class FilesView(ctk.CTkFrame):
    """
    GUI component that displays a list of user-selected files.
    Replaces the standard ttk.Treeview with a CTkScrollableFrame
    containing checkboxes and labels for a modern appearance.
    Includes playback controls for audio files.
    """
    def __init__(self, parent, audio_player: AudioPlayer, title="Wybrane", **kwargs):
        super().__init__(parent, width=300, **kwargs)
        self.grid_propagate(False)

        self.audio_player = audio_player

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=title, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # --- Scrollable Frame for File List ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=284)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        # --- Header ---
        header_checkbox = ctk.CTkLabel(self.scrollable_frame, text="", width=35)
        header_checkbox.grid(row=0, column=0, padx=(5,0), pady=2)

        header_filename = ctk.CTkLabel(self.scrollable_frame, text="Nazwa", width=150, anchor="w")
        header_filename.grid(row=0, column=1, padx=5, pady=2)

        header_duration = ctk.CTkLabel(self.scrollable_frame, text="Czas", width=50, anchor="center")
        header_duration.grid(row=0, column=2, padx=5, pady=2)

        header_play = ctk.CTkLabel(self.scrollable_frame, text="Odsłuchaj", width=50, anchor="center")
        header_play.grid(row=0, column=3, padx=5, pady=2)

        # --- Data Storage ---
        # List to store refs to (checkbox, file_path, duration_sec, play_button)
        self.file_widgets = []

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
            checkbox = ctk.CTkCheckBox(self.scrollable_frame, text="", width=35)
            checkbox.grid(row=i, column=0, padx=(5,0), pady=2)
            if not is_long:
                checkbox.select()

            # --- Filename Label ---
            filename_label = ctk.CTkLabel(self.scrollable_frame, text=filename, width=150, anchor="w")
            filename_label.grid(row=i, column=1, padx=5, pady=2)

            # --- Duration Label ---
            duration_label = ctk.CTkLabel(self.scrollable_frame, text=duration_str, width=50, anchor="center")
            duration_label.grid(row=i, column=2, padx=5, pady=2)

            # --- Play Button ---
            play_button = ctk.CTkButton(self.scrollable_frame, text="▶", width=30)
            play_button.grid(row=i, column=3, padx=5, pady=2)
            # Assign command after creation to use a fresh lambda scope
            play_button.configure(command=lambda fp=file_path: self.on_play_button_click(fp))

            if is_long:
                # Apply a visual cue for long files
                filename_label.configure(text_color="red")
                duration_label.configure(text_color="red")

            self.file_widgets.append((checkbox, file_path, duration_sec, play_button))

        self.update_play_buttons()

    def on_play_button_click(self, file_path):
        """Handles the click event for a play/pause button."""
        self.audio_player.toggle_play_pause(file_path)
        self.update_play_buttons()

    def update_play_buttons(self):
        """
        Updates the text of all play/pause buttons based on the audio player's state.
        This should be called whenever the player state might have changed.
        """
        if not self.file_widgets:
            return

        for _, file_path, _, button in self.file_widgets:
            state = self.audio_player.get_state(file_path)
            if state == 'playing':
                button.configure(text="⏸") # Pause symbol
            else:
                button.configure(text="▶") # Play symbol

    def get_checked_files(self):
        """
        Returns a list of full paths to the files that are currently checked.
        """
        checked_files = []
        for checkbox, file_path, _, _ in self.file_widgets:
            if checkbox.get() == 1: # 1 means checked
                checked_files.append(file_path)
        return checked_files

    def clear_view(self):
        """
        Clears the view by destroying all file entry widgets and resetting the data list.
        """
        # Stop any playback before clearing the view
        if self.audio_player:
            self.audio_player.stop()

        for widget in self.scrollable_frame.winfo_children():
            # Don't destroy the headers
            if widget.grid_info()["row"] > 0:
                widget.destroy()

        self.file_widgets.clear()