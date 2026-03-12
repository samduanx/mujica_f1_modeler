<#
.SYNOPSIS
    Run simulation with narrative assistance for Windows PowerShell

.DESCRIPTION
    This script runs the F1 simulation with optional narrative assistance
    to help guide outcomes for story-driven campaigns.

.PARAMETER Intensity
    The level of narrative assistance:
    - subtle: Minor adjustments for story flow
    - moderate: Balanced assistance (default)
    - strong: Significant narrative guidance

.PARAMETER TargetTeam
    The team to receive narrative assistance (default: Ferrari)

.EXAMPLE
    .\run_with_assist.ps1
    Runs with moderate assistance for Ferrari

.EXAMPLE
    .\run_with_assist.ps1 -Intensity strong -TargetTeam "Red Bull"
    Runs with strong assistance for Red Bull
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("subtle", "moderate", "strong")]
    [string]$Intensity = "moderate",

    [Parameter(Mandatory=$false)]
    [string]$TargetTeam = "Ferrari"
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Narrative Assistance Mode" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Intensity: $Intensity"
Write-Host "Target: $TargetTeam"
Write-Host ""

# Set environment variables
$env:F1_NARRATIVE_ASSIST = $Intensity
$env:F1_ASSIST_TARGET = $TargetTeam

# Run the simulation
Write-Host "Running simulation with narrative assistance..." -ForegroundColor Green
python main.py

# Cleanup
Remove-Item Env:\F1_NARRATIVE_ASSIST
Remove-Item Env:\F1_ASSIST_TARGET

Write-Host ""
Write-Host "Narrative assistance disabled." -ForegroundColor Yellow
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
