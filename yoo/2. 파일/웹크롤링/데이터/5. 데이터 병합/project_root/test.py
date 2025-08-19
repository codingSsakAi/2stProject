import os
from dotenv import load_dotenv

print(load_dotenv())
print("UPSTAGE_API_KEY:", os.getenv("UPSTAGE_API_KEY"))
print("PINECONE_API_KEY:", os.getenv("PINECONE_API_KEY"))