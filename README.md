# SkillSphere

A working implementation of all four SRS system features (Section 4):
User & Skill Management, AI Recommendation, Learning Request & Session
Management, and Feedback/Trust Score Management — plus an Admin
dashboard for verification and moderation.

Stack: **Flask + MySQL** backend, **React (Vite)** frontend.

## Requirement coverage

| Feature | Requirements | Status |
|---|---|---|
| 4.1 User & Skill Management | REQ-1..5, REQ-18, REQ-20/21 | ✅ |
| 4.2 AI Recommendation | REQ-6, REQ-7, REQ-8, REQ-9 | ✅ |
| 4.3 Learning Request & Session Management | REQ-10..13, REQ-19 | ✅ |
| 4.4 Feedback, Testing & Trust Score | REQ-14..17, REQ-22 | ✅ |
| Admin dashboard | business rule 5.5 | ✅ |
| Security (5.3) | password hashing, JWT expiry, HTTPS assumed at deploy, AI rate limiting | ✅ |

Detailed requirement-to-code mapping is in each blueprint's route
docstrings/comments (`app/auth`, `app/profile_mgmt`, `app/skills`,
`app/ai_engine`, `app/sessions`, `app/feedback`, `app/admin`,
`app/notifications`).

### Implementation notes / where this fills gaps the SRS leaves open

- **Two kinds of "verified".** REQ-2 is self-service email-link
  verification (`users.is_verified`) and gates basic login access.
  Business rule 5.5 ("only Admin may verify new user accounts") is a
  separate, stronger flag (`users.admin_verified`) set via the Admin
  dashboard, and *that* is what feeds the 10% "verification status"
  term in the REQ-15 trust-score formula.
- **AI Recommendation (4.2)** uses TF-IDF + cosine similarity
  (scikit-learn) for topic detection, and a hand-rolled
  frequency-based extractive summarizer for REQ-9 — per SRS 2.5, no
  GPU or external LLM service is assumed available. Falls back to
  keyword matching if scikit-learn isn't installed (assumption 2.7).
  Tutor ranking (REQ-7) weights: 40% topic relevance, 30% trust score,
  20% completed sessions (capped), 10% availability — this
  implementation's resolution of TBD-4; tune the constants in
  `app/ai_engine/nlp.py` if usage data suggests otherwise.
- **Notifications and search-history tables** aren't in SRS 6.1's
  entity list but are needed to make REQ-19 (in-app notifications) and
  REQ-8 ("related topics based on ... search history") concrete rather
  than aspirational.
- **Trust score simplifications** (documented in `app/trust.py`):
  completion rate = completed / (completed + cancelled); attendance
  rate is computed only among completed sessions. A production version
  would track an `accepted_at` timestamp to distinguish a request
  cancelled before vs. after acceptance.
- **REQ-19's 24-hour reminder** runs via a Flask CLI command
  (`flask send-reminders`) meant to be triggered by cron every
  15–30 minutes — see "Scheduled reminders" below. There's no
  always-on background worker process in this build.

## Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env with real values
```

Create the database (adjust credentials to match `.env`):

```bash
mysql -u root -p < schema.sql
```

Run the server:

```bash
python run.py        # http://localhost:5000
```

For local development without setting up real SMTP, leave
`MAIL_SUPPRESS_SEND=true` in `.env` — verification links and other
emails are printed to the console instead of sent.

### Scheduled reminders (REQ-19)

Run periodically (e.g. via cron or Windows Task Scheduler) to notify
both parties when an accepted session starts within 24 hours:

```bash
cd backend && source venv/bin/activate
flask --app run.py send-reminders
```

Example crontab entry (every 15 minutes):
```
*/15 * * * * cd /path/to/skillsphere/backend && venv/bin/flask --app run.py send-reminders
```

### Creating the first Admin account

There's no self-service admin signup (by design — business rule 5.5).
Register a normal account, then flip it to admin directly in the
database:

```sql
UPDATE users SET is_admin = TRUE WHERE email = 'coordinator@college.edu';
```
Log out and back in afterwards so the new JWT carries the admin claim.

## Frontend setup

```bash
cd frontend
npm install
npm run dev           # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:5000`.

## API summary

### Auth & Profile
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | – | Register (institutional email only) |
| POST | `/api/auth/verify-email` | – | Confirm email via token |
| POST | `/api/auth/login` | – | Log in, get JWT |
| GET | `/api/auth/me` | JWT | Current user |
| GET/PUT | `/api/profile` | JWT | View/edit own profile |
| GET | `/api/profile/<user_id>` | – | Public profile view |
| GET/POST | `/api/profile/availability` | JWT | List/add tutor availability |
| DELETE | `/api/profile/availability/<id>` | JWT | Remove a slot |
| GET | `/api/profile/progress` | JWT | Learner's topic checklist |

### Skills
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET/POST | `/api/skills`, `/api/skills/mine` | JWT | Manage own topics |
| PUT/DELETE | `/api/skills/<id>` | JWT | Edit/remove a topic |
| GET | `/api/skills/search?q=...` | – | Keyword topic search |

### AI Recommendation
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/ai/detect-topic` | JWT (rate-limited) | Detect topic, rank tutors, suggest related topics |

### Sessions
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/sessions` | JWT (learner) | Create a session request |
| GET | `/api/sessions/mine?role=&status=` | JWT | List my sessions |
| GET | `/api/sessions/<id>` | JWT | Session detail |
| POST | `/api/sessions/<id>/accept` | JWT (tutor) | Accept + schedule |
| POST | `/api/sessions/<id>/reject` | JWT (tutor) | Reject |
| POST | `/api/sessions/<id>/cancel` | JWT | Cancel (either party) |
| POST | `/api/sessions/<id>/complete` | JWT (tutor) | Close session, generate summary, update progress |
| GET | `/api/sessions/<id>/summary` | JWT | Retrieve the AI-generated summary |

### Feedback
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/api/sessions/<id>/review` | JWT (learner) | Rate + review, recalculates trust score |
| GET | `/api/tutors/<id>/reviews` | – | Public trust score + reviews |
| POST | `/api/sessions/<id>/report` | JWT | Report inappropriate behavior |

### Notifications
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/notifications` | JWT | List mine, unread first |
| POST | `/api/notifications/<id>/read` | JWT | Mark one read |
| POST | `/api/notifications/read-all` | JWT | Mark all read |

### Admin
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/api/admin/users` | Admin | List users |
| POST | `/api/admin/users/<id>/verify` | Admin | Admin-verify (REQ-15 trust component) |
| POST | `/api/admin/users/<id>/suspend` | Admin | Suspend account |
| POST | `/api/admin/users/<id>/unsuspend` | Admin | Lift suspension |
| DELETE | `/api/admin/users/<id>` | Admin | Hard-delete a user (cascades to their skills/sessions/reviews/reports) |
| GET | `/api/admin/reports?status=` | Admin | List flagged reports |
| POST | `/api/admin/reports/<id>/resolve` | Admin | Resolve, optionally suspend |
| GET | `/api/admin/stats` | Admin | Platform activity counts |

## Testing

Two backend smoke-test scripts were run against an in-memory SQLite DB
during development, covering every module end to end:

1. Register → verify → login → add skill → keyword search →
   availability → profile update → wrong-domain rejection.
2. Two tutors + a learner + an admin → AI topic detection → weighted
   tutor ranking → session request → accept → complete (with notes) →
   session summary generation → progress checklist update → review
   submission → trust-score formula verified against hand-calculated
   expected values → admin verification (trust-score bump) → report
   filed and resolved → non-admin blocked from admin routes →
   suspended user blocked from login → AI endpoint rate-limit trip.

No `pytest` suite is included yet — the smoke-test scripts are a good
starting point to convert into one.

## Working with Git

`.gitignore` already excludes `.env`, `venv/`, `node_modules/`, `dist/`,
and `__pycache__/`.

```bash
git init
git add .
git commit -m "Initial commit: full SkillSphere implementation"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Suggested next steps

1. Convert the smoke-test scripts into a real `pytest` suite (one file
   per module) and add CI.
2. Add pagination to `/api/skills/search`, `/api/sessions/mine`, and
   `/api/admin/users` — everything currently returns full result sets.
3. Track an `accepted_at` timestamp on sessions to make the
   completion-rate calculation in `app/trust.py` exact rather than
   approximate.
4. Move the AI corpus (`Skill.query.all()` on every request) to a
   cached/precomputed TF-IDF matrix if the skills table grows large —
   fine at PBL scale, not at real production scale.
5. Add a real online/offline session-mode integration (e.g. a video
   call link for "online" sessions) — currently just a label.
