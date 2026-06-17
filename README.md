# Konya

AI-powered benefits navigator for the USAII Hackathon 2026 (Direction A). Helps users check eligibility against policy documents through a guided, human-like interview.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env          # then add your FEATHERLESS_API_KEY
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Documentation

Technical and submission write-ups are kept locally (`konya-documentation.md`, `konya-submission.md`) and are not tracked in this repository.

## Tests

```bash
python manage.py test navigator.tests
```

## Stack

- Django 5
- Featherless AI (Llama 3.1 8B Instruct)
- SQLite (development)
