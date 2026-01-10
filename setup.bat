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

set "CUDA_TAG="
set "CUDA_VER="
for /f "tokens=9" %%A in ('cmd /c "nvidia-smi 2>nul ^| findstr /i \"CUDA Version\""') do set "CUDA_VER=%%A"
for /f "delims=" %%T in ('powershell -NoProfile -Command "$v='%CUDA_VER%'; if ($v -match '^(\\d+)\\.(\\d+)$') { $major=[int]$matches[1]; $minor=[int]$matches[2]; if ($major -gt 12 -or ($major -eq 12 -and $minor -ge 1)) { 'cu121' } elseif ($major -eq 11 -and $minor -ge 8) { 'cu118' } }"') do set "CUDA_TAG=%%T"
if defined CUDA_TAG (
  call :print_color Cyan "[setup] Detected CUDA %CUDA_VER%. Installing torch %CUDA_TAG%..."
  if "%CUDA_TAG%"=="cu121" python -m pip install --force-reinstall torch==2.2.2+cu121 --index-url https://download.pytorch.org/whl/cu121
  if "%CUDA_TAG%"=="cu118" python -m pip install --force-reinstall torch==2.2.2+cu118 --index-url https://download.pytorch.org/whl/cu118
) else (
  call :print_color DarkYellow "[setup] WARNING: No compatible CUDA version detected. Using CPU embeddings; initial indexing may be slow."
)

python -m pip install -U pip
python -m pip install -e .[dev]
if errorlevel 1 (
  call :print_color Red "[setup] Failed to install dependencies."
  pause
  exit /b 1
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
if not defined HINT_VER (
  for /f "delims=" %%V in ('powershell -NoProfile -Command "$paths=@(\"C:\\Program Files\\Unity\\Hub\\Editor\",\"C:\\Program Files\\Unity Hub\\Editor\",(Join-Path $env:LOCALAPPDATA 'Unity\\Hub\\Editor')); $versions=@(); foreach ($p in $paths) { if (Test-Path $p) { Get-ChildItem -Path $p -Directory | ForEach-Object { if ($_.Name -match '^(\\d{4}\\.\\d+)') { $versions += $matches[1] } } } } if ($versions.Count -gt 0) { $versions | Sort-Object { $_ -as [version] } | Select-Object -Last 1 }"') do set "HINT_VER=%%V"
  if defined HINT_VER (
    for /f "tokens=1,2 delims=." %%A in ("!HINT_VER!") do (
      set "HINT_SHORT=%%A.%%B"
    )
    if defined HINT_SHORT (
      set "DEFAULT_VER=!HINT_SHORT!"
      set "DETECTED_VER=!HINT_SHORT!"
    )
  )
)

goto :after_hint

:detect_hint
set "TEMP_PY=%TEMP%\unitydocs_hint_ver.py"
> "%TEMP_PY%" echo import os
>> "%TEMP_PY%" echo import re
>> "%TEMP_PY%" echo import pathlib
>> "%TEMP_PY%" echo import sys
>> "%TEMP_PY%" echo paths = [
>> "%TEMP_PY%" echo r"C:\Program Files\Unity\Hub\Editor",
>> "%TEMP_PY%" echo r"C:\Program Files\Unity Hub\Editor",
>> "%TEMP_PY%" echo os.path.join(os.environ.get("LOCALAPPDATA",""),"Unity","Hub","Editor"),
>> "%TEMP_PY%" echo "/Applications/Unity/Hub/Editor",
>> "%TEMP_PY%" echo os.path.expanduser("~/Applications/Unity/Hub/Editor"),
>> "%TEMP_PY%" echo ]
>> "%TEMP_PY%" echo versions = set()
>> "%TEMP_PY%" echo for base in paths:
>> "%TEMP_PY%" echo ^    p = pathlib.Path(base)
>> "%TEMP_PY%" echo ^    if p.is_dir():
>> "%TEMP_PY%" echo ^        for child in p.iterdir():
>> "%TEMP_PY%" echo ^            if child.is_dir():
>> "%TEMP_PY%" echo ^                m = re.search(r"(\\d{4}\\.\\d+)", child.name)
>> "%TEMP_PY%" echo ^                if m:
>> "%TEMP_PY%" echo ^                    versions.add(m.group(1))
>> "%TEMP_PY%" echo if versions:
>> "%TEMP_PY%" echo ^    def key(v): return tuple(int(x) for x in v.split("."))
>> "%TEMP_PY%" echo ^    sys.stdout.write(sorted(versions, key=key)[-1])
for /f "usebackq delims=" %%V in (`"%VENV%\Scripts\python.exe" "%TEMP_PY%"`) do set "HINT_VER=%%V"
del "%TEMP_PY%" >nul 2>&1
exit /b 0

:after_hint

if defined DETECTED_VER (
  set "SELECTED=%DETECTED_VER%"
  goto :write_config
)

:choose_version
echo.
call :print_color Green "Unity version %DEFAULT_VER% detected. Press Enter to continue or choose a different version:"
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
set "TEMP_CFG=%TEMP%\unitydocs_config.yaml"
(
  echo unity_version: "%SELECTED%"
  echo download_url: "https://cloudmedia-docs.unity3d.com/docscloudstorage/en/%SELECTED%/UnityDocumentation.zip"
  echo paths:
  echo   root: "data/unity/%SELECTED%"
  echo   raw_zip: "data/unity/%SELECTED%/raw/UnityDocumentation.zip"
  echo   raw_unzipped: "data/unity/%SELECTED%/raw/UnityDocumentation"
  echo   baked_dir: "data/unity/%SELECTED%/baked"
  echo   index_dir: "data/unity/%SELECTED%/index"
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
