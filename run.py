import os
import sys
import socket
from gevent import monkey

# Patch SSL first, before any other imports
monkey.patch_ssl()

# Now import other modules
from app import create_app, socketio
from config import Config

# Patch remaining modules
monkey.patch_socket()
monkey.patch_select()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))  # Changed to 0.0.0.0 to allow external connections
            return False
        except socket.error:
            return True

app = create_app()

if __name__ == '__main__':
    try:
        # Get port from environment variable or use default
        port = int(os.environ.get('PORT', 8000))
        
        # Check if port is available
        if is_port_in_use(port):
            print(f"Port {port} is already in use. Please stop any running instances.")
            sys.exit(1)
        
        print(f"Starting server on port {port}...")
        print("Server will be accessible at:")
        print(f"http://localhost:{port}/")
        print("Multiple users can connect to the same chatroom.")
        
        # Use socketio.run with gevent
        socketio.run(
            app,
            host='0.0.0.0',  # Changed to 0.0.0.0 to allow external connections
            port=port,
            debug=False,
            use_reloader=False,
            log_output=True,
            allow_unsafe_werkzeug=True
        )
        
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)
