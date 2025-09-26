# This file contains the component for the "Transcription" field.
# It consists of a label, a textbox, and a scrollbar.

import customtkinter as ctk

class TranscriptionView(ctk.CTkFrame):
    """
    GUI component for displaying the final transcription.
    """
    def __init__(self, parent, text, **kwargs):
        """
        Initializes the frame.

        Args:
            parent: The parent widget (main application window).
            text (str): The label to display above the textbox.
        """
        super().__init__(parent, **kwargs)

        # Grid configuration within the component
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Label
        self.label = ctk.CTkLabel(self, text=text, anchor="center")
        self.label.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Textbox for displaying transcription
        self.text = ctk.CTkTextbox(
            self,
            wrap="word",
            state="disabled",
            width=400,
            padx=8,
            pady=8
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def update_text(self, content):
        """Populates the textbox with the given text content."""
        self.text.configure(state="normal")
        self.text.delete('1.0', "end")
        try:
            self.text.insert("end", content)
        except Exception as e:
            print(f"Error updating transcription view: {e}")
        self.text.configure(state="disabled")

    def get_text(self):
        """Returns the entire content of the textbox."""
        return self.text.get("1.0", "end")

    def clear_view(self):
        """Clears the textbox."""
        self.text.configure(state="normal")
        self.text.delete('1.0', "end")
        self.text.configure(state="disabled")