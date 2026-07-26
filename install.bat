@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv 2>nul
if errorlevel 1 py -3.11 -m venv .venv
if errorlevel 1 python -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
echo 安装完成。双击 start.bat 启动。
pause
