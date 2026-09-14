import os

SESSION_COOKIE = "simver_session"
SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "7"))
PBKDF2_ITERATIONS = int(os.environ.get("PBKDF2_ITERATIONS", "200000"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0").lower() in ("1", "true", "yes", "on")
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCK_MINUTES = int(os.environ.get("LOGIN_LOCK_MINUTES", "15"))
COOKIE_PATH = "/"
COOKIE_SAMESITE = "lax"