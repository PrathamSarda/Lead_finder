git clone ...
cd company-lead-finder

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

python -m playwright install chromium

alembic upgrade head

uvicorn ...