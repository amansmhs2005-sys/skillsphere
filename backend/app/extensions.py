from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
cors = CORS()
# 5.3: "apply rate limiting to AI/NLP-based topic-detection queries"
limiter = Limiter(key_func=get_remote_address)
