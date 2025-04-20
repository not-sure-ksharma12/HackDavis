import os
import sys
import json
import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# --- Configuration ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "books"  # Database name is "books"
COLLECTION_NAME = "books"  # Collection name is "books"
CHUNK_PREVIEW_SIZE = 3000
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-ada-002"

print(f"🔍 MongoDB Configuration:")
print(f"MONGO_URI: {MONGO_URI}")
print(f"DB_NAME: {DB_NAME}")
print(f"COLLECTION_NAME: {COLLECTION_NAME}")

# --- Define Known Genres ---
KNOWN_GENRES = {"self-help", "devotional", "sci-fi", "biography"}

def get_user_collection(user_id):
    """Get the collection for a specific user."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def load_book(file_path):
    """Loads text content from .txt or .pdf files."""
    print(f"Attempting to load book from: {file_path}")
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif ext == ".pdf":
        loader = PyPDFLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    docs = loader.load()
    if not docs:
        raise ValueError("No content loaded from file.")

    print(f"Loaded {len(docs)} document parts.")
    full_text = "\n".join(doc.page_content for doc in docs if doc.page_content)
    if not full_text.strip():
        raise ValueError("Loaded content is empty or whitespace.")
    print(f"Total characters loaded: {len(full_text)}")
    return docs, full_text

def extract_metadata(text):
    """Uses GPT-4 to extract title, author, and genre from book text."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    print("🧠 Extracting metadata using LLM (gpt-4)...")
    llm = ChatOpenAI(model="gpt-4", temperature=0, api_key=OPENAI_API_KEY)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that extracts book metadata."),
        ("user", "Given the following content from a book, extract:\n"
                 "- Title of the book (string)\n"
                 "- Author name(s) (string or list of strings)\n"
                 "- Genre classification (string, choose the most appropriate primary genre)\n\n"
                 "Respond ONLY with a valid JSON object containing keys: \"title\", \"author\", \"genre\".\n\n"
                 "Book Content Snippet:\n{text}")
    ])
    chain = prompt | llm

    preview_text = text[:CHUNK_PREVIEW_SIZE]
    if not preview_text.strip():
        raise ValueError("Preview text for metadata extraction is empty.")

    result = chain.invoke({"text": preview_text})
    print("LLM Raw Output for Metadata:", result.content)

    try:
        content_cleaned = result.content.strip()
        if content_cleaned.startswith("json"):
            content_cleaned = content_cleaned[7:]
        if content_cleaned.endswith(""):
            content_cleaned = content_cleaned[:-3]
        
        metadata = json.loads(content_cleaned.strip())

        if not isinstance(metadata, dict):
            raise ValueError("LLM response was not a valid JSON object.")
        if not all(k in metadata for k in ["title", "author", "genre"]):
            print("⚠ LLM JSON response missing required keys (title, author, genre).")
            metadata.setdefault("title", "Unknown Title")
            metadata.setdefault("author", "Unknown Author")
            metadata.setdefault("genre", "Unknown")

        if isinstance(metadata.get("author"), list):
            metadata["author"] = ", ".join(metadata["author"]) if metadata["author"] else "Unknown Author"
        
        if not isinstance(metadata.get("genre"), str):
            metadata["genre"] = "Unknown"

        return metadata
    except json.JSONDecodeError as e:
        print(f"⚠ Could not parse JSON from model: {e}")
        print("Raw output:", result.content)
        return {"title": "Unknown Title", "author": "Unknown Author", "genre": "Unknown"}
    except Exception as e:
        print(f"An unexpected error occurred during metadata parsing: {e}")
        return {"title": "Unknown Title", "author": "Unknown Author", "genre": "Unknown"}

def chunk_and_embed(docs):
    """Splits documents into chunks and generates embeddings."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    print("Chunking documents...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    if not chunks:
        raise ValueError("No chunks generated after splitting.")
    print(f"📄 Generated {len(chunks)} chunks.")

    texts = [chunk.page_content for chunk in chunks]

    print("🤖 Generating embeddings...")
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    vectors = embeddings.embed_documents(texts)
    if len(vectors) != len(texts):
        raise ValueError("Mismatch between number of chunks and generated vectors.")
    print(f"🔢 Generated {len(vectors)} vectors.")

    return texts, vectors

def store_in_mongo(metadata, texts, vectors, file_path, uploaded_by=None):
    """Stores book metadata, text chunks, and embeddings in MongoDB."""
    print(f"📦 Connecting to MongoDB...")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Print database and collection info
    print(f"Connected to database: {db.name}")
    print(f"Using collection: {collection.name}")
    
    # List all collections in the database
    print("Available collections:", db.list_collection_names())
    
    extracted_genre = metadata.get("genre", "")
    final_genre = "Unknown"

    if isinstance(extracted_genre, str) and extracted_genre.strip():
        genre_lower = extracted_genre.strip().lower()
        if genre_lower in KNOWN_GENRES:
            final_genre = extracted_genre.strip().title().replace("Sci-Fi","Sci-Fi")
        else:
            print(f"⚠ Extracted genre '{extracted_genre}' not in known list. Assigning 'Unknown'.")
            final_genre = "Unknown"
    else:
        print(f"⚠ No valid genre extracted or found. Assigning 'Unknown'.")
        final_genre = "Unknown"

    # Check if book already exists
    existing_book = collection.find_one({
        "title": metadata.get("title", "Unknown Title"),
        "author": metadata.get("author", "Unknown Author")
    })

    if existing_book:
        print(f"⚠ Book '{metadata['title']}' by '{metadata['author']}' already exists.")
        return existing_book['_id']

    # If book is uploaded by user, use their name as author
    author = uploaded_by if uploaded_by else metadata.get("author", "Unknown Author")

    # Structure for the MongoDB document
    doc = {
        "file_path": file_path,
        "title": metadata.get("title", "Unknown Title"),
        "author": author,  # Use the uploaded_by name as author
        "genre": final_genre,
        "chunks": [
            {"text": text, "embedding": vector}
            for text, vector in zip(texts, vectors)
            if vector is not None
        ],
        "upload_date": datetime.datetime.utcnow()
    }

    print(f"💾 Inserting document for '{doc['title']}' (Genre: {doc['genre']}) into MongoDB...")
    print(f"Document to insert: {json.dumps(doc, default=str)}")
    
    result = collection.insert_one(doc)
    print(f"✅ Book stored in MongoDB with _id: {result.inserted_id}")
    
    # Verify the document was inserted
    inserted_doc = collection.find_one({"_id": result.inserted_id})
    print(f"Verified inserted document: {json.dumps(inserted_doc, default=str)}")
    
    client.close()
    return result.inserted_id

def process_book(file_path, uploaded_by=None):
    """Orchestrates the loading, metadata extraction, chunking, embedding, and storage."""
    print(f"📘 Processing book: {file_path}")

    try:
        # 1. Load
        docs, full_text = load_book(file_path)

        # 2. Extract Metadata
        metadata = extract_metadata(full_text)
        print("🧠 Metadata extracted:", metadata)

        # 3. Chunk and Embed
        texts, vectors = chunk_and_embed(docs)

        # 4. Store in MongoDB (includes genre check)
        mongo_id = store_in_mongo(metadata, texts, vectors, file_path, uploaded_by)

        print(f"🎉 Successfully processed and stored book with ID: {mongo_id}")
        return mongo_id

    except ValueError as ve:
        print(f"Error processing book: {ve}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_book.py <path_to_book>")
        sys.exit(1)

    book_path = sys.argv[1]
    if not os.path.exists(book_path):
        print(f"Error: File not found at {book_path}")
        sys.exit(1)

    process_book(book_path) 