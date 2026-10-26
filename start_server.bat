@echo off
title VidStudio AI Server
cd /d "C:\Users\howar\Desktop\APPS\MIS APPS\vidstudio-ai"
echo ========================================================
echo   VIDSTUDIO AI - Super Suite de Produccion & Outliers
echo   Acceso Local: http://localhost:8585
echo ========================================================
python -m uvicorn main:app --host 0.0.0.0 --port 8585
pause
