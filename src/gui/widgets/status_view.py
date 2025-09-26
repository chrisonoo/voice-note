# This file contains a generic component for "To Process" and "Processed" lists.
# It consists of a label, a list, and a counter panel.

import customtkinter as ctk
import os

class StatusView(ctk.CTkFrame):
    """
    GUI component that displays a list of files in a specific state (e.g., to be processed)
    with a dynamic counter.
    """
    def __init__(self, parent, text, **kwargs):
        """
        Initializes the frame.

        Args:
            parent: The parent widget (main application window).
            text (str): The label to display above the list (e.g., "To Process").
        """
        super().__init__(parent, **kwargs)

        # Grid configuration within the component
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Label
        self.label = ctk.CTkLabel(self, text=text, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Textbox for displaying file list
        self.text = ctk.CTkTextbox(
            self,
            wrap="word",
            state="disabled",
            width=150,
            padx=8,
            pady=8
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def update_from_list(self, file_paths):
        """Populates the textbox with a list of filenames."""
        self.text.configure(state="normal")
        self.text.delete('1.0', "end")
        try:
            # Convert full paths to filenames
            file_names = [os.path.basename(path) for path in file_paths if path]
            # Insert filenames into the textbox
            self.text.insert("end", '\n'.join(file_names))
        except Exception as e:
            print(f"Error updating status view: {e}")
        self.text.configure(state="disabled")

    def clear_view(self):
        """Clears the textbox."""
        self.text.configure(state="normal")
        self.text.delete('1.0', "end")
        self.text.configure(state="disabled")