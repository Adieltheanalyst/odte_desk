@echo off
cd /d C:\Users\Admin\Desktop\project_004
call .venv\Scripts\activate.bat
if not exist logs mkdir logs
python -m src.ingest.chain_snapshot >> logs\chain.log 2>&1