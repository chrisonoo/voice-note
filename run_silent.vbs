' Ten skrypt VBS uruchamia plik run_gui.bat w trybie ukrytym,
' co pozwala na uruchomienie aplikacji bez widocznego okna terminala.

' Utworzenie obiektu powłoki systemowej
Set WshShell = CreateObject("WScript.Shell")

' Pobranie pełnej ścieżki do folderu, w którym znajduje się ten skrypt VBS
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Zbudowanie pełnej ścieżki do pliku .bat, który ma być uruchomiony
batPath = """" & scriptDir & "\run_gui.bat" & """"

' Uruchomienie pliku .bat w trybie ukrytym (parametr 0)
WshShell.Run batPath, 0

' Zwolnienie obiektu z pamięci
Set WshShell = Nothing