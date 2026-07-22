# Spec: Data Filter Profile Page

## Overview
This feature adds filtering controls to the `/profile` page so a logged-in user can narrow down their transaction history and category breakdown by date range and category. The profile page already renders live data from the database (Step 5); Step 6 extends the existing query helpers to accept optional filter parameters and adds a filter form to the profile template. Stats, recent expenses, and category breakdown all respect the active filters, so the user can answer questions like "how much did I spend on Food last month?" without leaving the profile page. Filters live entirely in the URL (query string), making filtered views shareable and bookmarkable.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be a protected route)
- Step 4: Profile page UI (template must exist with the four sections)
- Step 5: Profile backend connection (query helpers must exist for the live data being filtered)

## Routes
- `GET /profile` — render the profile page with optional filters applied — logged-in only
  - Query params (all optional, all combinable):
    - `start_date` (YYYY-MM-DD) — include only expenses on or after this date
    - `end_date` (YYYY-MM-DD) — include only expenses on or before this date
    - `category` (one of: Food, Transport, Bills, Health, Entertainment, Shopping, Other) — include only expenses in this category

No new routes — filtering extends the existing `/profile` route.

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient. Filtering is applied at query time.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter form above the summary stats row containing:
    - `start_date` input (`<input type="date">`)
    - `end_date` input (`<input type="date">`)
    - `category` `<select>` with all seven categories plus an "All categories" default
    - Apply button (submits via GET to `/profile`)
    - Clear button (links to `/profile` with no query string)
  - When filters are active, show a small "Filtered: …" summary line and the total result count
  - When filters are active and the result set is empty, show an empty-state message instead of empty tables
  - All filter inputs must preserve their current value when the page re-renders (echo the submitted values)

## Files to change
- `app.py` — update the `/profile` route to:
  - Read `start_date`, `end_date`, `category` from `request.args`
  - Validate inputs (bad date format → ignore; unknown category → ignore)
  - Pass filter values into the new query helpers
  - Pass `filters_active` and `result_count` context to the template
- `database/db.py` — extend existing helpers to accept optional filter parameters:
  - `count_expenses_for_user(user_id, start_date=None, end_date=None, category=None)` — apply the same WHERE clauses
  - `get_total_spent_for_user(user_id, start_date=None, end_date=None, category=None)` — apply the same WHERE clauses
  - `get_top_category_for_user(user_id, start_date=None, end_date=None, category=None)` — apply the same WHERE clauses
  - `get_recent_expenses_for_user(user_id, limit=10, start_date=None, end_date=None, category=None)` — apply the same WHERE clauses
  - `get_category_breakdown_for_user(user_id, start_date=None, end_date=None, category=None)` — apply the same WHERE clauses
  - A small private `_apply_expense_filters(where_clauses, params, start_date, end_date, category)` helper builds the WHERE fragment so all five helpers stay in sync

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL, even when building dynamic WHERE clauses
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- The filter form submits via GET so the URL is shareable — do not use POST
- Filter values are echoed back into the form inputs so the page does not "reset" on submit
- An invalid `start_date` or `end_date` (e.g. unparseable string) is silently ignored — the page should still render with no date filter rather than 500
- An unknown `category` value is silently ignored and treated as "All categories"
- The seven allowed categories are: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- `start_date` and `end_date` are inclusive on both ends
- The recent-expenses `limit` parameter still defaults to 10 and is not user-configurable
- Filter form must work with all controls disabled/empty — i.e. submitting nothing is equivalent to the unfiltered view

## Definition of done
- [ ] `/profile` with no query params renders the unfiltered view (matches Step 5 behaviour)
- [ ] `/profile?category=Food` shows only Food expenses in the recent-expenses table and category breakdown
- [ ] `/profile?start_date=2025-01-01&end_date=2025-12-31` restricts all stats and the table to that date range
- [ ] Combining `start_date`, `end_date`, and `category` applies all three filters
- [ ] The filter form echoes the current values after submit
- [ ] An invalid date string (e.g. `?start_date=not-a-date`) is ignored and the page still renders
- [ ] An unknown category (e.g. `?category=NotReal`) is ignored and the page still renders
- [ ] When filters are active and no expenses match, the page shows an empty-state message
- [ ] Filtered URLs are shareable — pasting the URL into a new tab reproduces the filtered view
- [ ] `Clear filters` button on the form returns the user to the unfiltered `/profile`
- [ ] All five DB query helpers accept the new filter kwargs without breaking existing callers
- [ ] No hex colour values appear in `profile.html` — only CSS variables
