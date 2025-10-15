# GUI main module - graphical user interface entry point

def main():
    """Główna funkcja uruchamiająca aplikację w trybie graficznego interfejsu użytkownika (GUI)."""
    # Komentarz: Inicjalizacja bazy danych została przeniesiona do głównego pliku main.py,
    # aby uniknąć podwójnego wywołania przy starcie w trybie GUI. To dobra praktyka.
    from .main_window import App
    app = App()
    app.mainloop()  # `mainloop()` uruchamia główną pętlę zdarzeń Tkinter, która czeka na akcje użytkownika.
