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
if not exist "%VENV%\Scripts\activate.bat" (
  call :print_color Cyan "[setup] Creating venv at %VENV%..."
  call %PY_CMD% -m venv "%VENV%"
  if errorlevel 1 (
    call :print_color Red "[setup] Failed to create venv. Ensure Python 3.12+ is installed and on PATH."
    pause
    exit /b 1
  )
  call "%VENV%\Scripts\activate.bat"
) else (
  call "%VENV%\Scripts\activate.bat"
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
call :print_color Green "Select setup mode:"
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

call :print_color Cyan "[setup] Installing project dependencies..."

python -m pip install -U pip
if /i "%SETUP_MODE%"=="cuda" (
  python -m pip install -e ".[dev,vector]"
) else (
  python -m pip install -e ".[dev]"
)
if errorlevel 1 (
  call :print_color Red "[setup] Failed to install dependencies."
  pause
  exit /b 1
)

if /i "%SETUP_MODE%"=="cuda" (
  set "TORCH_OK="
  set "TORCH_CHANNEL="
  call :print_color Cyan "[setup] Installing CUDA torch build (cu128 -> cu121 -> cu118)..."
  call :try_torch_channel cu128
  if errorlevel 1 (
    call :try_torch_channel cu121
  )
  if errorlevel 1 (
    call :try_torch_channel cu118
  )

  if not defined TORCH_OK (
    call :print_color Red "[setup] Failed to install CUDA torch."
    pause
    exit /b 1
  )

  call :print_color Cyan "[setup] Installed torch from %TORCH_CHANNEL% index."

  python -c "import torch,sys; print('[setup] torch=' + str(torch.__version__) + ' cuda=' + str(torch.version.cuda) + ' available=' + str(torch.cuda.is_available())); raise SystemExit(0 if (torch.cuda.is_available() and torch.version.cuda is not None) else 1)"
  if errorlevel 1 (
    call :print_color Red "[setup] CUDA verification failed. Refusing to continue with CPU torch."
    pause
    exit /b 1
  )
)
if /i "%SETUP_MODE%"=="cpu" (
  call :print_color Yellow "[setup] CPU-only mode selected. Index will run in FTS-only mode."
)

set "DEFAULT_VER=6000.3"
set "HINT_VER="
set "DETECTED_VER="
if defined UNITY_VERSION set "HINT_VER=%UNITY_VERSION%"
if defined UNITY_EDITOR_VERSION set "HINT_VER=%UNITY_EDITOR_VERSION%"
if not defined HINT_VER call :detect_hint

if defined HINT_VER (
  for /f "tokens=1,2 delims=." %%A in ("!HINT_VER!") do (
    set "HINT_SHORT=%%A.%%B"
  )
  if defined HINT_SHORT (
    set "DEFAULT_VER=!HINT_SHORT!"
    set "DETECTED_VER=!HINT_SHORT!"
  )
)

goto :after_hint

:detect_hint
set "TEMP_PS=%TEMP%\unitydocs_hint_ver.ps1"
> "%TEMP_PS%" echo $paths = @("C:\Program Files\Unity\Hub\Editor","C:\Program Files\Unity Hub\Editor",($env:LOCALAPPDATA + "\Unity\Hub\Editor"))
>> "%TEMP_PS%" echo $versions = @()
>> "%TEMP_PS%" echo foreach ($p in $paths) {
>> "%TEMP_PS%" echo ^  if (Test-Path $p) {
>> "%TEMP_PS%" echo ^    foreach ($child in Get-ChildItem -Path $p -Directory) {
>> "%TEMP_PS%" echo ^      if ($child.Name -match '^(\\d{4}\\.\\d+)') { $versions += $matches[1] }
>> "%TEMP_PS%" echo ^    }
>> "%TEMP_PS%" echo ^  }
>> "%TEMP_PS%" echo }
>> "%TEMP_PS%" echo if ($versions.Count -gt 0) { $versions ^| Sort-Object { [version]$_ } ^| Select-Object -Last 1 }
for /f "delims=" %%V in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP_PS%"') do set "HINT_VER=%%V"
del "%TEMP_PS%" >nul 2>&1
exit /b 0

:after_hint

if defined DETECTED_VER (
  set "SELECTED=%DETECTED_VER%"
  goto :write_config
)

:choose_version
echo.
call :print_color Green "Select Unity docs version (default %DEFAULT_VER%):"
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
set "TEMP_CFG=%REPO%\config.yaml"
(
  echo unity_version: "%SELECTED%"
  echo download_url: "https://cloudmedia-docs.unity3d.com/docscloudstorage/en/%SELECTED%/UnityDocumentation.zip"
  echo paths:
  echo   root: "data/unity/%SELECTED%"
  echo   raw_zip: "data/unity/%SELECTED%/raw/UnityDocumentation.zip"
  echo   raw_unzipped: "data/unity/%SELECTED%/raw/UnityDocumentation"
  echo   baked_dir: "data/unity/%SELECTED%/baked"
  echo   index_dir: "data/unity/%SELECTED%/index"
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

python -c "from unity_docs_mcp.setup.ensure_artifacts import main; main()"
if errorlevel 1 (
  echo.
  call :print_color Red "[setup] Failed. Check the output above for details."
  pause
  exit /b 1
)
echo.
call :print_color Green "[setup] Success."
pause

goto :eof

:try_torch_channel
set "CHANNEL=%~1"
call :print_color Cyan "[setup] Trying torch from %CHANNEL%..."
python -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/%CHANNEL%
if errorlevel 1 (
  call :print_color DarkYellow "[setup] %CHANNEL% install failed."
  exit /b 1
)

python -c "import torch,sys; print('[setup] torch=' + str(torch.__version__) + ' cuda=' + str(torch.version.cuda) + ' available=' + str(torch.cuda.is_available())); raise SystemExit(0 if (torch.cuda.is_available() and torch.version.cuda is not None) else 1)"
if errorlevel 1 (
  call :print_color DarkYellow "[setup] %CHANNEL% installed but CUDA runtime verification failed."
  exit /b 1
)

set "TORCH_OK=1"
set "TORCH_CHANNEL=%CHANNEL%"
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

:print_color
powershell -NoProfile -Command "Write-Host '%~2' -ForegroundColor %~1"
exit /b 0
