from pymongo import MongoClient
import json

def check_and_create_index():
    # Connect to MongoDB
    MONGO_URI = "mongodb+srv://ksharma12:Kalpit123@cluster0.lh4ihuz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(MONGO_URI)
    db = client["books"]
    collection = db["books"]
    
    # Check if index exists
    indexes = collection.list_indexes()
    index_exists = False
    for index in indexes:
        if index.get("name") == "vector_index":
            index_exists = True
            print("Vector index already exists")
            break
    
    if not index_exists:
        print("Creating vector index...")
        # Create vector index
        index_definition = {
            "createIndexes": "books",
            "indexes": [
                {
                    "name": "vector_index",
                    "key": {
                        "chunks.embedding": "vector"
                    },
                    "vectorOptions": {
                        "dimensions": 1536,
                        "similarity": "cosine"
                    }
                }
            ]
        }
        
        try:
            result = db.command(index_definition)
            print("Vector index created successfully")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error creating index: {e}")
    
    # Verify the index
    print("\nCurrent indexes:")
    for index in collection.list_indexes():
        print(json.dumps(index, indent=2))

if __name__ == "__main__":
    check_and_create_index() 