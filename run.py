from app import create_app
from config import DEBUG


application = create_app()

if __name__ == "__main__":
    application.run(debug=DEBUG, port=5010)
