@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
if not exist logs mkdir logs
python -m src.ingest.chain_snapshot >> logs\chain.log 2>&1