from functools import wraps
from flask import session, redirect, url_for, current_app
import os
from dotenv import load_dotenv

load_dotenv()

# Auth0 configuration
AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_CALLBACK_URL = os.getenv('AUTH0_CALLBACK_URL', 'http://localhost:8000/callback')
AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE', f'https://{AUTH0_DOMAIN}/api/v2/')

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def get_user_info():
    return session.get('profile', {}) 