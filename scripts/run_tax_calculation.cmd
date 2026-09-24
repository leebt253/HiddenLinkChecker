@echo off
setlocal EnableExtensions DisableDelayedExpansion

pushd "%~dp0.."
if errorlevel 1 (
    echo Cannot open the HiddenLinkChecker project directory.
    exit /b 1
)

set "INPUT_PATH="
set /p "INPUT_PATH=Enter input JSON path: "
if not defined INPUT_PATH (
    echo Input path is required.
    popd
    exit /b 1
)

for %%I in ("%INPUT_PATH%") do (
    set "INPUT_FULL_PATH=%%~fI"
    set "INPUT_EXTENSION=%%~xI"
    set "OUTPUT_PATH=%%~dpI%%~nI.result.json"
)

if /I not "%INPUT_EXTENSION%"==".json" (
    echo Input file must have a .json extension.
    popd
    exit /b 1
)

if not exist "%INPUT_FULL_PATH%" (
    echo Input file not found: "%INPUT_FULL_PATH%"
    popd
    exit /b 1
)

set "PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Python environment not found: "%PYTHON%"
    popd
    exit /b 1
)

"%PYTHON%" "%~dp0run_tax_calculation.py" "%INPUT_FULL_PATH%" "%OUTPUT_PATH%"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo Tax calculation failed with exit code %EXIT_CODE%.
    popd
    exit /b %EXIT_CODE%
)

echo Output file: "%OUTPUT_PATH%"
popd
exit /b 0