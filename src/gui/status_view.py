# This file contains a generic component for "To Process" and "Processed" lists.
# It consists of a label, a list, and a counter panel.

import tkinter as tk
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

    def update_from_file(self, file_path):
        """Reads a text file and inserts its content into the textbox, showing only filenames."""
        self.text.configure(state="normal")
        self.text.delete('1.0', "end")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Convert full paths to filenames
                    lines = content.strip().split('\n')
                    file_names = []
                    for line in lines:
                        line = line.strip()
                        if line:  # Skip empty lines
                            file_name = os.path.basename(line)
                            file_names.append(file_name)

                    # Insert filenames into the textbox
                    self.text.insert("end", '\n'.join(file_names))
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
        self.text.configure(state="disabled")

    def clear_view(self):
        """Clears the textbox."""
        self.text.configure(state="normal")
        self.text.delete('1.0', "end")
        self.text.configure(state="disabled")