from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for, current_app
from flask_socketio import emit, join_room, leave_room
from app import socketio, mongo_client
from app.models.message import Message
from app.auth import requires_auth, get_user_info
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
from app import rag_pipeline  # Import from app directly
import pytz
from urllib.parse import urlencode, quote_plus
import requests
import json
from werkzeug.utils import secure_filename
import tempfile
from backend.process_book import process_book

load_dotenv()

main = Blueprint('main', __name__)
pdt = pytz.timezone('America/Los_Angeles')

# Use the global MongoDB connection for books
books_db = mongo_client["books"]
books_collection = books_db["books"]

@main.route('/')
def index():
    # If user is logged in, show their home page
    if session.get('profile'):
        return render_template('home.html', user_info=session['profile'])
    # If not logged in, show public home page
    return render_template('home.html', user_info=None)

@main.route('/login')
def login():
    # Get the full URL from the request
    protocol = 'https' if 'chatbook-app.loca.lt' in request.headers.get('Host', '') else 'http'
    host = request.headers.get('Host', 'localhost:8000')
    callback_url = f"{protocol}://{host}/callback"
    
    print(f"Login callback URL: {callback_url}")  # Debug print
    
    return current_app.auth0.authorize_redirect(
        redirect_uri=callback_url,
        audience=f"https://{os.getenv('AUTH0_DOMAIN')}/api/v2/"
    )

@main.route('/callback')
def callback():
    try:
        # Get the token
        token = current_app.auth0.authorize_access_token()
        
        # Get user info
        resp = current_app.auth0.get('userinfo')
        userinfo = resp.json()
        
        # Store the user information in flask session
        session['jwt_payload'] = userinfo
        session['profile'] = {
            'user_id': userinfo['sub'],
            'name': userinfo['name'],
            'picture': userinfo['picture']
        }
        return redirect(url_for('main.chat', username=userinfo['name']))
    except Exception as e:
        print(f"Error in callback: {str(e)}")
        return redirect(url_for('main.index'))

@main.route('/logout')
def logout():
    session.clear()
    protocol = 'https' if 'chatbook-app.loca.lt' in request.headers.get('Host', '') else 'http'
    host = request.headers.get('Host', 'localhost:8000')
    return_url = f"{protocol}://{host}/"
    
    print(f"Logout return URL: {return_url}")  # Debug print
    
    return redirect(
        'https://' + os.getenv('AUTH0_DOMAIN') + '/v2/logout?' +
        urlencode({
            'returnTo': return_url,
            'client_id': os.getenv('AUTH0_CLIENT_ID'),
            'federated': ''
        }, quote_via=quote_plus)
    )

@main.route('/<username>')
@requires_auth
def chat(username):
    session['username'] = username
    messages = Message.get_all_messages()
    
    # Fetch books from the books database
    books = list(books_collection.find({}, {'_id': 1, 'title': 1, 'author': 1}))
    # Convert ObjectId to string for JSON serialization
    for book in books:
        book['_id'] = str(book['_id'])
    
    return render_template('chat.html', 
                         username=username, 
                         messages=messages,
                         books=books,
                         user_info=get_user_info())

@socketio.on('connect')
def handle_connect():
    username = session.get('username', 'Anonymous')
    join_room('chat_room')
    emit('status', {
        'msg': f"{username} has joined",
        'timestamp': datetime.now(pytz.UTC).astimezone(pdt).strftime('%Y-%m-%d %H:%M:%S %Z')
    }, room='chat_room', broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username', 'Anonymous')
    leave_room('chat_room')
    leave_room(request.sid)  # Leave personal room
    emit('status', {
        'msg': f"{username} has left",
        'timestamp': datetime.now(pytz.UTC).astimezone(pdt).strftime('%Y-%m-%d %H:%M:%S %Z')
    }, room='chat_room')

@socketio.on('message')
def handle_message(data):
    username = session.get('username', 'Anonymous')
    user_id = session.get('profile', {}).get('user_id')  # Get Auth0 user ID
    message = Message(username=username, content=data['message'], user_id=user_id)
    message.save()
    
    # Emit to all clients
    emit('new_message', {
        'username': username,
        'user_id': user_id,
        'content': data['message'],
        'timestamp': datetime.now(pytz.UTC).astimezone(pdt).strftime('%Y-%m-%d %H:%M:%S %Z'),
        'message_type': 'chat'
    }, broadcast=True)

@socketio.on('book_question')
def handle_book_question(data):
    username = session.get('username', 'Anonymous')
    user_id = session.get('profile', {}).get('user_id')  # Get Auth0 user ID
    book_id = data.get('book_id')
    question = data.get('question')
    
    if not book_id or not question:
        emit('error', {'message': 'Missing book_id or question'})
        return
    
    try:
        # Get book title
        book = books_collection.find_one({'_id': ObjectId(book_id)})
        if not book:
            emit('error', {'message': 'Book not found'})
            return
            
        book_title = book.get('title', 'Unknown Book')
        
        # Get answer from RAG pipeline
        answer = rag_pipeline.ask_question(question, ObjectId(book_id), book_title)
        
        # Save message
        message = Message(
            username=username,
            user_id=user_id,
            content={
                'question': question,
                'answer': answer,
                'book_title': book_title
            },
            message_type='book_qa',
            book_id=book_id
        )
        message.save()
        
        # Emit to all clients
        emit('new_message', {
            'username': username,
            'user_id': user_id,
            'content': {
                'question': question,
                'answer': answer,
                'book_title': book_title
            },
            'timestamp': datetime.now(pytz.UTC).astimezone(pdt).strftime('%Y-%m-%d %H:%M:%S %Z'),
            'message_type': 'book_qa'
        }, broadcast=True)
        
    except Exception as e:
        print(f"Error processing book question: {e}")
        emit('error', {'message': str(e)})

@socketio.on('help_me_ai')
def handle_help_me_ai():
    try:
        print("Help me AI socket event received")
        
        # Get the last 5 messages from the database
        messages = Message.get_last_n_messages(5)
        print(f"Retrieved {len(messages)} messages from database")
        
        # Format the messages for Gemini
        conversation = "\n".join([
            f"{msg.username}: {msg.content if isinstance(msg.content, str) else msg.content.get('question', '')}"
            for msg in messages
        ])
        print("Formatted conversation:", conversation)
        
        # First, ask Gemini to summarize the conversation into a single question
        summary_prompt = f"""Based on the following conversation, identify the main question or topic the user is trying to understand. 
        Summarize it into a single, clear question that captures the essence of what they want to know:

{conversation}

Please provide only the question, nothing else."""
        
        # Call Gemini API to get the summary question
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            'Content-Type': 'application/json'
        }
        summary_data = {
            "contents": [{
                "parts": [{"text": summary_prompt}]
            }]
        }
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("Error: GEMINI_API_KEY not found in environment variables")
            emit('error', {'message': 'API key not configured'})
            return
            
        print("Making request to Gemini API for summary...")
        summary_response = requests.post(
            f"{url}?key={api_key}",
            headers=headers,
            json=summary_data
        )
        
        if summary_response.status_code != 200:
            emit('error', {'message': f'Failed to get summary: {summary_response.text}'})
            return
            
        summary_result = summary_response.json()
        summary_question = summary_result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        
        if not summary_question:
            emit('error', {'message': 'Failed to generate summary question'})
            return
            
        print("Generated summary question:", summary_question)
        
        # Now get the answer to the summarized question
        answer_prompt = f"""Please provide a clear and helpful answer to this question:

{summary_question}

Make your response concise but informative."""
        
        answer_data = {
            "contents": [{
                "parts": [{"text": answer_prompt}]
            }]
        }
        
        print("Making request to Gemini API for answer...")
        answer_response = requests.post(
            f"{url}?key={api_key}",
            headers=headers,
            json=answer_data
        )
        
        if answer_response.status_code != 200:
            emit('error', {'message': f'Failed to get answer: {answer_response.text}'})
            return
            
        answer_result = answer_response.json()
        ai_response = answer_result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        
        if not ai_response:
            emit('error', {'message': 'No answer received'})
            return
            
        print("AI response received:", ai_response)
        
        # Save the AI response as a message
        username = session.get('username', 'Anonymous')
        user_id = session.get('profile', {}).get('user_id')
        full_response = f"Based on your conversation, I understand you want to know: {summary_question}\n\n{ai_response}"
        message = Message(
            username="AI Assistant",
            content=full_response,
            user_id="ai_assistant",
            message_type="ai_help"
        )
        message.save()
        print("Message saved to database")
        
        # Emit the message
        emit('new_message', {
            'username': "AI Assistant",
            'user_id': "ai_assistant",
            'content': full_response,
            'timestamp': datetime.now(pytz.UTC).astimezone(pdt).strftime('%Y-%m-%d %H:%M:%S %Z'),
            'message_type': 'ai_help'
        }, broadcast=True)
        
    except Exception as e:
        print(f"Error in help_me_ai: {str(e)}")
        import traceback
        print(traceback.format_exc())
        emit('error', {'message': str(e)})

@main.route('/upload-book', methods=['POST'])
@requires_auth
def upload_book():
    try:
        print("🔍 Book upload request received")
        
        if 'bookFile' not in request.files:
            print("🔍 No file part in request")
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['bookFile']
        if not file or not file.filename:
            print("🔍 No file selected")
            return jsonify({'error': 'No selected file'}), 400
        
        filename = secure_filename(file.filename)
        if not filename.lower().endswith(('.pdf', '.txt')):
            print(f"🔍 Invalid file type: {filename}")
            return jsonify({'error': 'Invalid file type. Only PDF and TXT files are allowed.'}), 400
        
        # Get the user's name from the Auth0 session
        user_profile = session.get('profile', {})
        user_name = user_profile.get('name', 'Unknown User')
        print(f"🔍 Uploading book for user: {user_name}")
        
        # Create a temporary file to store the uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Process the book and store it in MongoDB
            print(f"🔍 Processing book: {temp_file_path}")
            # Pass the user's name as the author
            book_id = process_book(temp_file_path, uploaded_by=user_name)
            print(f"🔍 Book processed successfully with ID: {book_id}")
            
            # Get the book details to return
            book = books_collection.find_one({'_id': book_id})
            if book:
                return jsonify({
                    'message': 'Book uploaded successfully',
                    'book_id': str(book_id),
                    'title': book.get('title', 'Unknown Title'),
                    'author': book.get('author', user_name),  # Use the stored author
                    'genre': book.get('genre', 'Unknown')
                }), 200
            else:
                return jsonify({
                    'message': 'Book uploaded but details not found',
                    'book_id': str(book_id)
                }), 200
            
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
                print(f"🔍 Temporary file cleaned up: {temp_file_path}")
            except Exception as e:
                print(f"🔍 Error cleaning up temporary file: {e}")
                
    except Exception as e:
        print(f"🔍 Error in upload_book: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    
