@echo off
call ../.venv/Scripts/activate.bat
python -m mp_remote upload_path --path ./ESP-LED-Blink
pause