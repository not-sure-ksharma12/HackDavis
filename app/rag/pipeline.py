import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from scipy.spatial.distance import cosine as cosine_distance
import numpy as np
import redis
from pymongo import MongoClient
import json
from bson import ObjectId
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://ksharma12:Kalpit123@cluster0.lh4ihuz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = "books"
COLLECTION_NAME = "books"
INDEX_NAME = "vector_index"
EMBEDDING_MODEL = "text-embedding-ada-002"
LLM_MODEL = "gpt-3.5-turbo"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_TTL = 3600  # Cache time-to-live in seconds (1 hour)

# Verify OpenAI API key is set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

class RAGPipeline:
    def __init__(self):
        try:
            # Initialize MongoDB
            self.mongo_client = MongoClient(MONGO_URI)
            self.mongo_collection = self.mongo_client[DB_NAME][COLLECTION_NAME]
            
            # Test MongoDB connection
            self.mongo_client.admin.command('ping')
            logger.info("MongoDB connection successful.")
            
            # Initialize OpenAI components
            try:
                self.embeddings = OpenAIEmbeddings()
                logger.info("OpenAI Embeddings initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing embeddings: {e}")
                raise
            
            try:
                self.llm = ChatOpenAI(
                    model_name=LLM_MODEL,
                    temperature=0.1,
                    max_tokens=1000
                )
                logger.info("ChatOpenAI initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing LLM: {e}")
                raise
            
            # Initialize Redis for caching (make it optional)
            self.redis_client = None
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST, 
                    port=REDIS_PORT,
                    decode_responses=True,
                    socket_timeout=5,  # Add timeout
                    socket_connect_timeout=5  # Add connection timeout
                )
                self.redis_client.ping()
                logger.info("Redis connection successful.")
            except Exception as e:
                logger.warning(f"Redis connection failed, continuing without caching: {e}")
                self.redis_client = None
            
            # Initialize RAG chain
            self._initialize_rag_chain()
            logger.info("RAG pipeline initialized successfully.")
            
        except Exception as e:
            logger.error(f"Error initializing RAG pipeline: {e}")
            raise

    def _initialize_rag_chain(self):
        self.rag_template = """You are PagePal, an AI assistant that embodies the book "{book_title}". You are the book itself, speaking directly to the reader.

Your task is to answer questions based ONLY on the following context from the book. If the context doesn't contain the answer, say so politely.

Guidelines:
1. Answer as if you are the book speaking
2. Use a conversational, friendly tone
3. If the context doesn't answer the question, say "I don't have that information in my pages" or similar
4. Never make up information not present in the context
5. Structure your answer as a single, well-flowing paragraph
6. Do not use any markdown formatting, headers, or bullet points
7. Make the response concise and clear
8. End with a friendly conclusion

Format your answer like this:

[Write a single, well-flowing paragraph that answers the question using information from the context. Include key details and examples. Make it conversational and easy to understand. Do not use any markdown formatting, headers, or bullet points.]

I hope this helps you understand [topic] better! Feel free to ask if you'd like to explore any part in more detail.

Context:
{context}

Question: {question}
Answer:"""
        
        self.rag_prompt = PromptTemplate.from_template(self.rag_template)
        
        self.rag_chain = (
            {
                "context": RunnablePassthrough() | (lambda input_dict: self.retrieve_context(input_dict['query'], filter_criteria=input_dict.get('filter'))),
                "question": RunnablePassthrough() | (lambda input_dict: input_dict['query']),
                "book_title": RunnablePassthrough() | (lambda input_dict: input_dict.get('book_title', 'the book'))
            }
            | self.rag_prompt
            | self.llm
            | StrOutputParser()
        )

    def _get_cache_key(self, query, book_id):
        return f"rag:{book_id}:{query}"

    def _get_from_cache(self, cache_key):
        if not self.redis_client:
            return None
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Error getting from cache: {e}")
        return None

    def _set_in_cache(self, cache_key, result):
        if not self.redis_client:
            return
        try:
            self.redis_client.setex(
                cache_key,
                CACHE_TTL,
                json.dumps(result)
            )
        except Exception as e:
            logger.warning(f"Error setting cache: {e}")

    def retrieve_context(self, query: str, book_id: str) -> str:
        """Retrieve relevant context from MongoDB using text-based search."""
        try:
            # Clean and normalize the query
            query = query.lower().strip()
            
            # Handle explanation requests
            if query.startswith('explain'):
                # Remove 'explain' and clean up the query
                topic = query.replace('explain', '').strip()
                # Create a more comprehensive search pattern
                search_pattern = f"{topic}|{topic.split()[0]}"
            else:
                search_pattern = query

            # Search in chunks.text, title, and author fields
            results = self.mongo_collection.aggregate([
                {"$match": {"_id": ObjectId(book_id)}},
                {"$unwind": "$chunks"},
                {"$match": {
                    "$or": [
                        {"chunks.text": {"$regex": search_pattern, "$options": "i"}},
                        {"title": {"$regex": search_pattern, "$options": "i"}},
                        {"author": {"$regex": search_pattern, "$options": "i"}}
                    ]
                }},
                {"$project": {
                    "text": "$chunks.text",
                    "title": 1,
                    "author": 1,
                    "score": {
                        "$add": [
                            {"$multiply": [
                                {"$size": {"$split": ["$chunks.text", search_pattern]}},
                                10
                            ]},
                            {"$strLenCP": "$chunks.text"}
                        ]
                    }
                }},
                {"$sort": {"score": -1}},
                {"$limit": 5}
            ])

            candidate_chunks = list(results)
            
            if not candidate_chunks:
                return "I don't have that information in my pages."

            # Format the context
            context_parts = []
            for chunk in candidate_chunks:
                context_parts.append(f"From {chunk.get('title', 'Unknown Title')} by {chunk.get('author', 'Unknown Author')}:")
                context_parts.append(chunk['text'])
            
            return "\n\n".join(context_parts)

        except Exception as e:
            print(f"Error retrieving context: {str(e)}")
            return "I encountered an error while searching for information."

    def generate_response(self, query: str, context: str, book_title: str) -> str:
        """Generate a response using the LLM."""
        try:
            # Clean and normalize the query
            query = query.lower().strip()
            
            # Handle explanation requests
            if query.startswith('explain'):
                topic = query.replace('explain', '').strip()
                prompt = f"""You are explaining {topic} from the book "{book_title}".
                Use the following context to provide a clear, concise explanation.
                Write in a single paragraph that flows naturally.
                Include key details and examples from the context.
                Make it conversational and easy to understand.
                Do not use any markdown formatting, headers, or bullet points.

                Context:
                {context}

                Question: {query}
                Answer:"""
            else:
                prompt = self.rag_template.format(
                    book_title=book_title,
                    context=context,
                    question=query
                )

            # Get the response from the LLM
            response = self.llm.invoke(prompt)
            
            # Handle different response types
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'text'):
                return response.text
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I encountered an error while generating a response."

    def ask_question(self, query, book_id, book_title=None):
        """Ask a question about a specific book."""
        try:
            # Convert book_id to ObjectId if it's a string
            if isinstance(book_id, str):
                book_id = ObjectId(book_id)
            
            # Get context from the book
            context = self.retrieve_context(query, book_id)
            
            # If no context found, return early
            if context == "I don't have that information in my pages.":
                return context
            
            # Generate response
            response = self.generate_response(query, context, book_title or "the book")
            return response
            
        except Exception as e:
            print(f"Error in ask_question: {str(e)}")
            return "I'm having trouble processing your question right now. Please try again later."

# Create a global instance
try:
    logger.info("Initializing RAG pipeline...")
    rag_pipeline = RAGPipeline()
    logger.info("RAG pipeline initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize RAG pipeline: {e}")
    rag_pipeline = None
