# UPS-Logistics

Booking-time fraud detection for account-billed shipments.

The problem: packages booked on a legitimate shipper’s account are usually caught only after delivery, once the real shipper disputes the charge. The carrier then reverses the invoice and keeps the cost of a package that already moved.

The approach: a synchronous risk check on the ship confirm step, before a tracking number or label is issued. Start with rules and the billed account’s own history, in shadow mode, on account-billed shipments only.

See [docs/booking-fraud-approach.md](docs/booking-fraud-approach.md).

Architecture, in the order the confirm call runs: [docs/architecture.md](docs/architecture.md). Tables: [docs/schema.sql](docs/schema.sql). Picture: [docs/architecture.png](docs/architecture.png).

Round 1 deck (7 minutes + Q&A): [docs/Round1-Idea-and-Solution-Design.pptx](docs/Round1-Idea-and-Solution-Design.pptx). Speaker notes are the script. In PowerPoint, use View → Notes. Slide 11 is a Q&A appendix; do not present it in the 7 minutes.

System flow image: [docs/system-flow.png](docs/system-flow.png).

## Prototype

A confirm screen and a review queue. `POST /v1/booking-risk` runs the five rules, then an XGBoost score. The score can hold a booking. It cannot block one. The note is written from the reason codes. Set `OPENAI_API_KEY` if you want GPT-4.1 mini to rewrite that note; the action stays the one the rules chose.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Pick a case. Reset clears the queue and restores the seeded burst on Quiet Books. The database is SQLite at `backend/data/prototype.db`. Set `DATABASE_URL` to use Postgres.
