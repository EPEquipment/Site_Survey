@echo off
echo Starting EP Site Survey Tool...
call .\gradio-survey\Scripts\activate.bat
.\gradio-survey\Scripts\python.exe app.py
pause