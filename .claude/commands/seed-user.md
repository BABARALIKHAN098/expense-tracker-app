# Create a Single Dummy User in the Database

## Description

Create a single dummy user in the database.

## Allowed Tools

- Read
- Bash (`python3:*`)

## Task

Read `database/db.py` to understand:

- The `users` table schema.
- The `get_db()` helper function.

Then write and run a Python script using **Bash** that performs the following steps:

1. Generate a realistic random Indian user using your own knowledge of common Indian names from different regions.

2. Generate the following user details:
   - **Name:** A realistic Indian first and last name.
   - **Email:** Derived from the name with a random 2–3 digit number suffix.
     - Example:
       ```
       rahul.sharma91@gmail.com
       ```
   - **Password:** `"password123"` hashed using `werkzeug.security.generate_password_hash`.
   - **created_at:** Current date and time.

3. Check whether the generated email already exists in the `users` table.
   - If it exists, regenerate a new user until a unique email is produced.

4. Insert the user into the database using the same `get_db()` pattern found in `database/db.py`.

5. Print a confirmation containing:
   - `id`
   - `name`
   - `email`