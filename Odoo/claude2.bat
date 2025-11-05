@echo off
set ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic
set ANTHROPIC_AUTH_TOKEN=5f12c2e4b24640628573a3445b3d1bcc.SvOXXy089SvrlL6B
set ANTHROPIC_MODEL=glm-4.6
echo Using Z.AI API (GLM-4.6): %ANTHROPIC_BASE_URL%
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\QUOCTHINH\.local\bin\claude-glm.ps1" %*
