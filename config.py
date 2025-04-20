from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://ksharma12:Kalpit123@cluster0.lh4ihuz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'chatbook')
    
    # Auth0 Configuration
    AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN', 'dev-1ao4ofawr25h1fea.us.auth0.com')
    AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID', 'ccbMcFy7wEWXWgunS0f6I5FkMBai0wkh')
    AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET', 'rezh11vDEBrX4hi13Qk6xfAitwpHVHD_5FvBMK_SMmu66_jGO0e4X987DmVmnY0j')
    AUTH0_CALLBACK_URL = os.getenv('AUTH0_CALLBACK_URL', 'http://localhost:8000/callback')
