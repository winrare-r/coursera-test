@echo off
set SCRIPT_DIR=%~dp0
set EXE_PATH=%SCRIPT_DIR%dist\seti-analyzer\seti-analyzer.exe

if exist "%EXE_PATH%" (
    "%EXE_PATH%" %*
) else (
    echo Release сборка не найдена. Запускаем из исходников.
    python -m app.main %*
)
