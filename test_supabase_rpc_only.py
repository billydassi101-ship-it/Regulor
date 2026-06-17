import os
import sys
from dotenv import load_dotenv

backend_dir = r"C:\Users\User\Desktop\regulor\backend"
sys.path.append(backend_dir)

load_dotenv(r"C:\Users\User\Desktop\regulor\.env", override=True)

try:
    from supabase import create_client
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    print(f"Connecting with URL: {url}")
    supabase = create_client(url, key)
    
    # Mock embedding vector of length 384
    mock_emb = [0.0] * 384
    
    print("Calling match_documents RPC with mock embedding (no match_threshold)...")
    response = supabase.rpc(
        "match_documents",
        {
            "query_embedding": mock_emb,
            "match_count": 5,
        }
    ).execute()
    print("RPC Success! Response data count:", len(response.data))
    if response.data:
        print("First result similarity:", response.data[0].get("similarity"))
        print("First result content snippet:", response.data[0].get("content")[:100])
except Exception as e:
    print(f"Error calling match_documents: {e}")
