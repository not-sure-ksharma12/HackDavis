from pymongo import MongoClient
import json

def check_database():
    # Connect to MongoDB
    MONGO_URI = "mongodb+srv://ksharma12:Kalpit123@cluster0.lh4ihuz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(MONGO_URI)
    
    # List all databases
    print("Available databases:")
    databases = client.list_database_names()
    for db_name in databases:
        if db_name not in ['admin', 'local']:  # Skip system databases
            print(f"\nChecking database: {db_name}")
            db = client[db_name]
            
            # List all collections in the database
            collections = db.list_collection_names()
            print(f"Collections in {db_name}:", collections)
            
            # Check each collection
            for collection_name in collections:
                collection = db[collection_name]
                doc_count = collection.count_documents({})
                print(f"\nCollection '{collection_name}' has {doc_count} documents")
                
                # Get sample document structure (keys only)
                if doc_count > 0:
                    sample_doc = collection.find_one({})
                    print("Document structure (keys):", list(sample_doc.keys()))
                    if 'chunks' in sample_doc:
                        print(f"Number of chunks: {len(sample_doc['chunks'])}")

if __name__ == "__main__":
    check_database() 