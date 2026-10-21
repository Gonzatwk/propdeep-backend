@echo off
rem PropDeep en el PC: arranca el backend y la web y abre el navegador.
cd /d "%~dp0"
if exist venv\Scripts\activate.bat (set ACT=venv\Scripts\activate.bat) else if exist .venv\Scripts\activate.bat (set ACT=.venv\Scripts\activate.bat) else (echo No encuentro el venv ^(venv o .venv^) en esta carpeta.& pause & exit /b 1)
if not exist web\.env.local (echo VITE_API_URL=http://localhost:8000> web\.env.local)
if not exist web\node_modules (pushd web & call npm install & popd)
start "PropDeep API" cmd /k "call %ACT% && uvicorn main:app"
start "PropDeep web" cmd /k "cd web && npm run dev"
timeout /t 8 >nul
start "" http://localhost:5173/partidos
