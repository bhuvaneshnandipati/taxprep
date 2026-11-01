"""Test configuration: one throw-away SQLite DB per run, set before the app is imported."""
import os, tempfile, pathlib

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="taxprep-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["MAX_USERS"] = "100000"            # tests create many accounts
os.environ["MAX_SIGNUPS_PER_IP_PER_DAY"] = "100000"
os.environ["ADMIN_EMAILS"] = "boss@test.com,boss2@test.com"
os.environ["ADMIN_SETUP_CODE"] = "test-setup-code"
os.environ.setdefault("JWT_SECRET", "test-secret")
from cryptography.fernet import Fernet
os.environ["DATA_KEY"] = Fernet.generate_key().decode()
