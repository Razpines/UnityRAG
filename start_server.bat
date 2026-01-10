@echo off
setlocal

REM Start the unity-docs MCP server over HTTP with a visible log window.
REM Optional: pass a port as the first argument (default 8765).

set "REPO=%~dp0"
set "VENV=%REPO%\.venv"
if not exist "%VENV%\Scripts\activate.bat" (
  echo [start_server] venv not found at %VENV%\Scripts\activate.bat
  exit /b 1
)

call "%VENV%\Scripts\activate.bat"

set "UNITY_DOCS_MCP_ROOT=%REPO%"
if "%~1" neq "" (
  set "UNITY_DOCS_MCP_PORT=%~1"
)

echo [start_server] UNITY_DOCS_MCP_ROOT=%UNITY_DOCS_MCP_ROOT%
if defined UNITY_DOCS_MCP_PORT (
  echo [start_server] Using port %UNITY_DOCS_MCP_PORT%
) else (
  echo [start_server] Using default port 8765
)

unitydocs-mcp-http
