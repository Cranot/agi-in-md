#!/usr/bin/env python3
"""Test file for OPTIMIZE mode validation.

Known issues (for manual verification):
1. SQL injection via unsanitized user input
2. Hardcoded credentials in config
3. Missing input validation on user data
4. No error handling in critical paths
5. Insecure deserialization (pickle)
"""

import pickle
import os

# Issue 1: SQL injection
def get_user(db, user_id):
    """Vulnerable to SQL injection."""
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

# Issue 2: Hardcoded credentials
DATABASE_URL = "postgresql://admin:password123@localhost/mydb"
API_KEY = os.environ['API_KEY']

# Issue 3: Missing input validation
def process_user_input(data):
    """No validation of input type or content."""
    result = data.upper()
    return result.split(',')

# Issue 4: No error handling
def load_config(path):
    """No exception handling."""
    with open(path) as f:
        return f.read()

# Issue 5: Insecure deserialization
def load_user_session(session_data):
    """Pickle is insecure — attacker can execute code."""
    return pickle.loads(session_data)

# Poor error handling
def save_to_file(path, data):
    """No validation, no error handling."""
    file = open(path, 'w')
    file.write(data)
    file.close()
