from datetime import datetime
from app import mongo_client
from bson import json_util
import json
import pytz

class Message:
    def __init__(self, username, content, user_id=None, message_type='chat', book_id=None):
        self.username = username
        self.user_id = user_id  # Auth0 sub ID
        self.content = content
        pdt = pytz.timezone('America/Los_Angeles')
        self.timestamp = datetime.now(pytz.UTC).astimezone(pdt)
        self.message_type = message_type
        self.book_id = book_id

    def to_dict(self):
        return {
            'username': self.username,
            'user_id': self.user_id,
            'content': self.content,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'message_type': self.message_type,
            'book_id': self.book_id
        }

    def save(self):
        return mongo_client.chatbook.messages.insert_one(self.to_dict())

    @staticmethod
    def get_all_messages():
        messages = list(mongo_client.chatbook.messages.find().sort('timestamp', 1))
        # Convert MongoDB documents to JSON-serializable dictionaries
        return [
            {
                'username': msg.get('username'),
                'user_id': msg.get('user_id'),
                'content': msg.get('content'),
                'timestamp': msg.get('timestamp'),
                'message_type': msg.get('message_type'),
                'book_id': msg.get('book_id')
            }
            for msg in messages
        ]

    @staticmethod
    def get_last_n_messages(n):
        messages = list(mongo_client.chatbook.messages.find().sort('timestamp', -1).limit(n))
        # Convert MongoDB documents to Message objects
        return [
            Message(
                username=msg.get('username'),
                content=msg.get('content'),
                user_id=msg.get('user_id'),
                message_type=msg.get('message_type'),
                book_id=msg.get('book_id')
            )
            for msg in messages
        ]
