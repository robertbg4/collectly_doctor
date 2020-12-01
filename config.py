import os


def get_required_env(var_name):
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"enviroment variable {var_name} is not set")
    return value


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DRCHRONO_CLIENT_ID = get_required_env("DRCHRONO_CLIENT_ID")
DRCHRONO_CLIENT_SECRET = get_required_env("DRCHRONO_CLIENT_SECRET")
DRCHRONO_REFRESH_TOKEN = get_required_env("DRCHRONO_REFRESH_TOKEN")

SECRET_KEY = get_required_env("SECRET_KEY")

DOCTOR_ID = get_required_env("DOCTOR_ID")
OFFICE_ID = get_required_env("OFFICE_ID")
EXAM_ROOM = get_required_env("EXAM_ROOM")
