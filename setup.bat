@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "REPO=%~dp0"
for %%I in ("%REPO%.") do set "REPO=%%~fI"
set "VENV=%REPO%\.venv"
set "PY_CMD="
set "REQUIRED_GB=20"
set "PY_PORTABLE=%REPO%\.python"
set "PY_PORTABLE_EXE=%PY_PORTABLE%\python.exe"
set "PY_PORTABLE_VER=3.12.8"
set "PY_PORTABLE_ZIP=python-%PY_PORTABLE_VER%-embed-amd64.zip"
set "PY_PORTABLE_URL=https://www.python.org/ftp/python/%PY_PORTABLE_VER%/%PY_PORTABLE_ZIP%"
set "SETUP_DIAG_PATH=%REPO%\reports\setup\setup-diagnostics-latest.json"

call :__setup_main
set "SETUP_EXIT=%ERRORLEVEL%"
call :write_setup_diagnostics %SETUP_EXIT%
if not "%SETUP_EXIT%"=="0" (
  call :print_color Yellow "[setup] Summary: mode=%SETUP_MODE% unity_version=%SELECTED%"
  if exist "%SETUP_DIAG_PATH%" (
    call :print_color Yellow "[setup] Diagnostics snapshot: %SETUP_DIAG_PATH%"
  )
  call :report_hint
)
exit /b %SETUP_EXIT%

:__setup_main
if exist "%REPO%\banner.txt" (
  type "%REPO%\banner.txt"
) else (
  call :print_color Cyan "UnityRAG"
)

if exist "%PY_PORTABLE_EXE%" (
  set "PY_CMD=\"%PY_PORTABLE_EXE%\""
  goto :python_ok
)

python -c "import sys; raise SystemExit(0 if sys.version_info>=(3,12) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "PY_CMD=python"
  goto :python_ok
)

:try_py_launcher
for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do (
  set "PY_CMD=py -3.12"
  goto :python_ok
)

if not defined PY_CMD (
  call :print_color Yellow "[setup] Python 3.12+ not found on PATH."
  call :print_color Yellow "[setup] You can install it globally, or let this repo download a portable copy."
  set /p INSTALL_PORTABLE=Download portable Python %PY_PORTABLE_VER% into .python? [Y/n]:
  if /i "%INSTALL_PORTABLE%"=="n" (
    call :print_color Red "[setup] Install Python 3.12+ and re-run this script."
    pause
    exit /b 1
  )
  call :install_portable_python
  if errorlevel 1 (
    call :print_color Red "[setup] Failed to install portable Python."
    pause
    exit /b 1
  )
  set "PY_CMD=\"%PY_PORTABLE_EXE%\""
)

:python_ok
set "DRIVE=%REPO:~0,1%"
for /f "delims=" %%F in ('powershell -NoProfile -Command "(Get-PSDrive -Name '%DRIVE%').Free/1GB -as [int]"') do set "FREE_GB=%%F"
if defined FREE_GB if %FREE_GB% LSS %REQUIRED_GB% (
  call :print_color Red "[setup] Not enough disk space on drive %DRIVE%:. Need at least %REQUIRED_GB% GB free."
  call :print_color Red "[setup] Free space detected: %FREE_GB% GB."
  pause
  exit /b 1
)

set "SETUP_MODE="
if /i "%UNITYDOCS_SETUP_MODE%"=="cuda" set "SETUP_MODE=cuda"
if /i "%UNITYDOCS_SETUP_MODE%"=="1" set "SETUP_MODE=cuda"
if /i "%UNITYDOCS_SETUP_MODE%"=="cpu" set "SETUP_MODE=cpu"
if /i "%UNITYDOCS_SETUP_MODE%"=="2" set "SETUP_MODE=cpu"

if not defined SETUP_MODE goto choose_mode
goto after_choose_mode

:choose_mode
echo.
call :print_color Green "[detect] Select setup mode:"
echo   1^) CUDA ^(hybrid retrieval: FTS + vectors^)
echo   2^) CPU-only ^(FTS-only retrieval; no transformers/faiss^)
echo.
set "SETUP_MODE="
set /p MODE_CHOICE=Mode [1]:
if "%MODE_CHOICE%"=="" set "MODE_CHOICE=1"
if /i "%MODE_CHOICE%"=="1" set "SETUP_MODE=cuda"
if /i "%MODE_CHOICE%"=="cuda" set "SETUP_MODE=cuda"
if /i "%MODE_CHOICE%"=="2" set "SETUP_MODE=cpu"
if /i "%MODE_CHOICE%"=="cpu" set "SETUP_MODE=cpu"
if not defined SETUP_MODE (
  call :print_color Red "Invalid mode selection."
  goto choose_mode
)

:after_choose_mode

call :print_color Cyan "[bootstrap] Preparing virtual environment and dependencies..."
set "PYTHONPATH=%REPO%\src"
call %PY_CMD% -m unity_docs_mcp.setup.bootstrap --repo-root "%REPO%" --venv "%VENV%" --mode "%SETUP_MODE%"
set "PYTHONPATH="
if errorlevel 1 (
  call :print_color Red "[bootstrap] Failed to prepare dependencies."
  pause
  exit /b 1
)
call "%VENV%\Scripts\activate.bat"

set "DEFAULT_VER=6000.3"
call :print_color Cyan "[detect] Inspecting installed Unity editors..."
set "PYTHONPATH=%REPO%\src"
call %PY_CMD% -m unity_docs_mcp.setup.unity_detect
for /f "delims=" %%V in ('call %PY_CMD% -m unity_docs_mcp.setup.unity_detect --suggest-only 2^>nul') do set "DEFAULT_VER=%%V"
set "PYTHONPATH="

:choose_version
echo.
call :print_color Green "[detect] Select Unity docs version (default %DEFAULT_VER%):"
echo.
echo Options: 6000.5, 6000.4, 6000.3, 6000.0
echo Note: Unity 2022 and older are likely already well-known by LLMs.
echo Use 6000.x when you need current docs and citations.
echo.
set /p CHOICE=Version [default %DEFAULT_VER%]:

if "%CHOICE%"=="" set "SELECTED=%DEFAULT_VER%"
if /i "%CHOICE%"=="1" set "SELECTED=6000.5"
if /i "%CHOICE%"=="2" set "SELECTED=6000.4"
if /i "%CHOICE%"=="3" set "SELECTED=6000.3"
if /i "%CHOICE%"=="4" set "SELECTED=6000.0"
if /i "%CHOICE%"=="6000.5" set "SELECTED=6000.5"
if /i "%CHOICE%"=="6000.4" set "SELECTED=6000.4"
if /i "%CHOICE%"=="6000.3" set "SELECTED=6000.3"
if /i "%CHOICE%"=="6000.0" set "SELECTED=6000.0"

if not defined SELECTED (
  call :print_color Red "Invalid selection. Please choose a supported version."
  goto choose_version
)

:write_config
set "TEMP_CFG=%REPO%\config.local.yaml"
(
  echo index:
  echo   lexical: "sqlite_fts5"
  if /i "%SETUP_MODE%"=="cuda" (
    echo   vector: "faiss"
  ) else (
    echo   vector: "none"
  )
) > "%TEMP_CFG%"

set "UNITY_DOCS_MCP_ROOT=%REPO%"
set "UNITY_DOCS_MCP_CONFIG=%TEMP_CFG%"
set "UNITY_DOCS_MCP_CLEANUP=1"
set "UNITY_DOCS_MCP_UNITY_VERSION=%SELECTED%"

call :print_color Cyan "[artifacts] Ensuring local docs artifacts..."
python -c "from unity_docs_mcp.setup.ensure_artifacts import main; main()"
if errorlevel 1 (
  echo.
  call :print_color Red "[artifacts] Failed. Check the output above for details."
  pause
  exit /b 1
)

call :configure_mcp

echo.
call :print_color Green "[setup] Success."
pause

goto :eof

:configure_mcp
set "MCP_CLIENT="
if /i "%UNITYDOCS_MCP_CLIENT%"=="codex" set "MCP_CLIENT=codex"
if /i "%UNITYDOCS_MCP_CLIENT%"=="claude" set "MCP_CLIENT=claude"
if /i "%UNITYDOCS_MCP_CLIENT%"=="both" set "MCP_CLIENT=both"
if /i "%UNITYDOCS_MCP_CLIENT%"=="skip" set "MCP_CLIENT=skip"
if /i "%UNITYDOCS_MCP_CLIENT%"=="none" set "MCP_CLIENT=skip"
if /i "%UNITYDOCS_MCP_CLIENT%"=="0" set "MCP_CLIENT=skip"

if defined MCP_CLIENT goto apply_mcp

:choose_mcp
echo.
call :print_color Green "[mcp] Auto-configure MCP client now?"
echo   1^) Codex ^(recommended^)
echo   2^) Claude Desktop
echo   3^) Both
echo   4^) Skip
echo.
set "MCP_CLIENT="
set /p MCP_CHOICE=Choice [1]:
if "%MCP_CHOICE%"=="" set "MCP_CHOICE=1"
if /i "%MCP_CHOICE%"=="1" set "MCP_CLIENT=codex"
if /i "%MCP_CHOICE%"=="codex" set "MCP_CLIENT=codex"
if /i "%MCP_CHOICE%"=="2" set "MCP_CLIENT=claude"
if /i "%MCP_CHOICE%"=="claude" set "MCP_CLIENT=claude"
if /i "%MCP_CHOICE%"=="3" set "MCP_CLIENT=both"
if /i "%MCP_CHOICE%"=="both" set "MCP_CLIENT=both"
if /i "%MCP_CHOICE%"=="4" set "MCP_CLIENT=skip"
if /i "%MCP_CHOICE%"=="skip" set "MCP_CLIENT=skip"
if /i "%MCP_CHOICE%"=="none" set "MCP_CLIENT=skip"
if not defined MCP_CLIENT (
  call :print_color Red "Invalid selection."
  goto choose_mcp
)

:apply_mcp
if /i "%MCP_CLIENT%"=="skip" (
  call :print_color Cyan "[setup] Skipping MCP client auto-config."
  exit /b 0
)

if /i "%MCP_CLIENT%"=="codex" goto install_codex
if /i "%MCP_CLIENT%"=="claude" goto install_claude
if /i "%MCP_CLIENT%"=="both" (
  goto install_codex
)
exit /b 0

:install_codex
python -m unity_docs_mcp.setup.mcp_config --client codex --repo-root "%REPO%" --unity-version "%SELECTED%"
if errorlevel 1 (
  call :print_color Yellow "[setup] Warning: failed to auto-configure Codex MCP."
)
if /i "%MCP_CLIENT%"=="both" goto install_claude
exit /b 0

:install_claude
python -m unity_docs_mcp.setup.mcp_config --client claude --repo-root "%REPO%" --unity-version "%SELECTED%"
if errorlevel 1 (
  call :print_color Yellow "[setup] Warning: failed to auto-configure Claude MCP."
)
exit /b 0

:install_portable_python
set "TEMP_ZIP=%TEMP%\%PY_PORTABLE_ZIP%"
set "TEMP_PIP=%TEMP%\get-pip.py"
call :print_color Cyan "[setup] Downloading portable Python %PY_PORTABLE_VER%..."
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PY_PORTABLE_URL%' -OutFile '%TEMP_ZIP%'" >nul 2>&1
if errorlevel 1 exit /b 1
if exist "%PY_PORTABLE%" rmdir /s /q "%PY_PORTABLE%"
powershell -NoProfile -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%PY_PORTABLE%'" >nul 2>&1
if errorlevel 1 exit /b 1
del "%TEMP_ZIP%" >nul 2>&1
if not exist "%PY_PORTABLE_EXE%" exit /b 1

if not exist "%PY_PORTABLE%\Lib\site-packages" mkdir "%PY_PORTABLE%\Lib\site-packages"
powershell -NoProfile -Command "$pth = Join-Path '%PY_PORTABLE%' 'python312._pth'; $c = Get-Content $pth; if (-not ($c -match 'Lib\\\\site-packages')) { Add-Content $pth 'Lib\\site-packages' }; $c = Get-Content $pth; $c = $c -replace '^#?import site','import site'; Set-Content $pth $c" >nul 2>&1
if errorlevel 1 exit /b 1

echo [setup] Installing pip into portable Python...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP_PIP%'" >nul 2>&1
if errorlevel 1 exit /b 1
"%PY_PORTABLE_EXE%" "%TEMP_PIP%" >nul 2>&1
if errorlevel 1 exit /b 1
del "%TEMP_PIP%" >nul 2>&1
exit /b 0

:write_setup_diagnostics
set "SNAP_STATUS=success"
set "SNAP_OUTCOME=setup.bat-success"
if not "%~1"=="0" (
  set "SNAP_STATUS=failed"
  set "SNAP_OUTCOME=setup.bat-failed"
)
if not defined PY_CMD exit /b 0
set "PYTHONPATH=%REPO%\src"
call %PY_CMD% -m unity_docs_mcp.setup.diagnostics --repo-root "%REPO%" --status "%SNAP_STATUS%" --mode "%SETUP_MODE%" --unity-version "%SELECTED%" --config-path "%UNITY_DOCS_MCP_CONFIG%" --outcome "%SNAP_OUTCOME%" --print-latest-path-only >nul 2>nul
set "PYTHONPATH="
exit /b 0

:report_hint
set "REPORT_VER=6000.3"
if defined SELECTED set "REPORT_VER=%SELECTED%"
call :print_color Yellow "[setup] Setup failed. Generate diagnostics with:"
call :print_color Yellow "        set UNITY_DOCS_MCP_UNITY_VERSION=%REPORT_VER% && unitydocs report --summary setup.bat-failed --prefill-issue"
exit /b 0

:print_color
powershell -NoProfile -Command "Write-Host '%~2' -ForegroundColor %~1"
exit /b 0
