' Этот скрипт запускает run_gui.bat в скрытом режиме, чтобы избежать появления окна терминала.

Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "run_gui.bat" & Chr(34), 0
Set WshShell = Nothing