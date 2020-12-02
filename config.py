import os


DEBUG = os.getenv("DEBUG", False) in ("True", True, "true")
IN_TEST = os.getenv("IN_TEST", False) in ("True", True, "true")


def get_required_env(var_name):
    if IN_TEST:
        return "test"
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"enviroment variable {var_name} is not set")
    return value


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.getenv("SECRET_KEY", "secret_key")

DRCHRONO_CLIENT_ID = get_required_env("DRCHRONO_CLIENT_ID")
DRCHRONO_CLIENT_SECRET = get_required_env("DRCHRONO_CLIENT_SECRET")
DRCHRONO_REFRESH_TOKEN = get_required_env("DRCHRONO_REFRESH_TOKEN")

DOCTOR_ID = get_required_env("DOCTOR_ID")
OFFICE_ID = get_required_env("OFFICE_ID")
EXAM_ROOM = get_required_env("EXAM_ROOM")

REQUEST_ATTEMPT_LIMIT = 3
