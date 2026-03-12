@echo off
REM Run simulation with narrative assistance for Windows
REM Usage: run_with_assist.bat [intensity] [target_team]
REM   intensity: subtle, moderate, strong (default: moderate)
REM   target_team: team name (default: Ferrari)

setlocal enabledelayedexpansion

REM Default values
set "INTENSITY=moderate"
set "TARGET=Ferrari"

REM Parse arguments
if not "%~1"=="" set "INTENSITY=%~1"
if not "%~2"=="" set "TARGET=%~2"

echo ==========================================
echo Narrative Assistance Mode
echo ==========================================
echo Intensity: %INTENSITY%
echo Target: %TARGET%
echo.

REM Set environment variables
set "F1_NARRATIVE_ASSIST=%INTENSITY%"
set "F1_ASSIST_TARGET=%TARGET%"

REM Run the simulation
echo Running simulation with narrative assistance...
python main.py

REM Cleanup
set "F1_NARRATIVE_ASSIST="
set "F1_ASSIST_TARGET="

echo.
echo Narrative assistance disabled.
pause
