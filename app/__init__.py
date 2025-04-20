from flask import Flask
from flask_socketio import SocketIO
from config import Config
from app.rag.pipeline import RAGPipeline  # Import RAGPipeline at the top
from authlib.integrations.flask_client import OAuth

# Initialize SocketIO with gevent
socketio = SocketIO(
    async_mode='gevent',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# Create global variables
mongo_client = None
db = None
rag_pipeline = None

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize Auth0
    oauth = OAuth(app)
    oauth.register(
        'auth0',
        client_id=Config.AUTH0_CLIENT_ID,
        client_secret=Config.AUTH0_CLIENT_SECRET,
        api_base_url=f'https://{Config.AUTH0_DOMAIN}',
        access_token_url=f'https://{Config.AUTH0_DOMAIN}/oauth/token',
        authorize_url=f'https://{Config.AUTH0_DOMAIN}/authorize',
        client_kwargs={
            'scope': 'openid profile email',
        },
        server_metadata_url=f'https://{Config.AUTH0_DOMAIN}/.well-known/openid-configuration'
    )
    app.auth0 = oauth.auth0  # Make auth0 available on the app instance
    
    # Initialize MongoDB connection
    global mongo_client, db
    from pymongo import MongoClient
    mongo_client = MongoClient(
        Config.MONGO_URI,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        serverSelectionTimeoutMS=30000,
        tls=True,
        tlsAllowInvalidCertificates=True  # Allow invalid certificates
    )
    db = mongo_client[Config.DATABASE_NAME]
    
    # Initialize SocketIO with the app
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        websocket=True,
        async_mode='gevent'
    )
    
    # Initialize RAG pipeline before importing routes
    global rag_pipeline
    if rag_pipeline is None:  # Only initialize if not already initialized
        rag_pipeline = RAGPipeline()
    
    # Import routes after initializing rag_pipeline
    from app.routes import main
    app.register_blueprint(main)
    
    return app
