import os

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
PORT = int(os.environ.get("PORT", 8001))
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
