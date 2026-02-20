@echo off
setlocal

set "REPO=%~dp0"
set "VENV=%REPO%\.venv"
if not exist "%VENV%\Scripts\activate.bat" (
  echo [start_server] venv not found at %VENV%\Scripts\activate.bat
  exit /b 1
)

if exist "%REPO%\\banner.txt" (
  type "%REPO%\\banner.txt"
)

cd /d "%REPO%"
if "%~1" neq "" (
  set "UNITY_DOCS_MCP_PORT=%~1"
)

call "%VENV%\Scripts\activate.bat"

python -c "from unity_docs_mcp.mcp_server import main_http; main_http()"
