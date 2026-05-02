import os

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24
PORT = int(os.environ.get("PORT", 8000))
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
