import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai

load_dotenv()

try:
    from pinecone import Pinecone, ServerlessSpec
    
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    INDEX_NAME = os.getenv("PINECONE_INDEX", "magichour-agent")

    if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
        pc.create_index(name=INDEX_NAME, dimension=3072, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
        print(f"Created Pinecone index: {INDEX_NAME}")

    index = pc.Index(INDEX_NAME)
    PINECONE_AVAILABLE = True

except Exception as e:
    print(f"Pinecone not configured yet: {e}")
    print("Memory features will be disabled until PINECONE_API_KEY is set")
    PINECONE_AVAILABLE = False


def embed_text(text: str) -> list:
    from google import genai
    embed_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    result = embed_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values

def store_character_memory():
    """Store consistent descriptions of Mira and the Wizard"""
    if not PINECONE_AVAILABLE:
        return

    characters = [
        {
            "id": "character_mira",
            "text": """
            Mira is a consistent main character: early 20s girl, big expressive eyes, messy wavy hair, 
            gentle and curious personality, slightly clumsy. Always wears the same cozy oversized cream hoodie 
            and casual clothes. Used in all Pixar/Disney-style animated stories.
            """,
            "type": "character",
            "name": "Mira"
        },
        {
            "id": "character_wizard",
            "text": """
            Magic Hour Wizard: Small, cute, slightly clumsy wizard with a big floppy hat, round glasses, 
            and a glowing wand. Playful, goofy, friendly, chaotic-good energy. He appears as a magical helper 
            who triggers transformations in niche stories.
            """,
            "type": "character",
            "name": "Magic Hour Wizard"
        }
    ]

    vectors = []
    for char in characters:
        vector = embed_text(char["text"])
        vectors.append({
            "id": char["id"],
            "values": vector,
            "metadata": {
                "type": "character",
                "name": char["name"],
                "description": char["text"]
            }
        })

    index.upsert(vectors=vectors)
    print("Stored consistent character memory (Mira + Wizard)")

def get_character_description(name: str) -> str:
    if not PINECONE_AVAILABLE:
        return ""
    
    try:
        query = embed_text(f"Description of {name} character in stories")
        results = index.query(
            vector=query,
            top_k=1,
            filter={"type": "character", "name": name},
            include_metadata=True
        )
        matches = results.get("matches", [])
        if matches:
            return matches[0]["metadata"].get("description", "")
    except:
        pass
    return ""

def store_generated_content(content_data: dict):
    if not PINECONE_AVAILABLE:
        return

    text = (f"World: {content_data.get('world_name', '')} "
            f"Format: {content_data.get('format_used', '')} "
            f"Niche: {content_data.get('niche', '')} "
            f"Type: {content_data.get('content_type', '')}")

    content_id = f"gen_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    index.upsert(vectors=[{
        "id": content_id,
        "values": embed_text(text),
        "metadata": {
            "world_name": content_data.get("world_name") or "",
            "format_used": content_data.get("format_used") or "",
            "niche": content_data.get("niche") or "general",
            "content_type": content_data.get("content_type") or "",
            "episode_title": content_data.get("episode_title") or "",
            "generated_at": datetime.utcnow().isoformat(),
            "type": "generated_content"
        }
    }])


def get_recent_content(days: int = 7) -> list[dict]:
    if not PINECONE_AVAILABLE:
        return []

    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Simple query to get recent items
        query = embed_text("recently generated magic hour content")
        results = index.query(
            vector=query,
            top_k=30,
            filter={"type": "generated_content"},
            include_metadata=True
        )
        
        recent = []
        for match in results.get("matches", []):
            meta = match["metadata"]
            if meta.get("generated_at", "") > cutoff:
                recent.append({
                    "world": meta.get("world_name"),
                    "format": meta.get("format_used"),
                    "niche": meta.get("niche")
                })
        return recent
    except:
        return []

def store_video_performance(video_data):
    if not PINECONE_AVAILABLE:
        print("Pinecone not available, skipping memory storage")
        return
    
    metrics = video_data.get("metrics", {})
    views = max(metrics.get("views", 1), 1)
    conversion_score = (
        (metrics.get("profile_visits", 0) * 3) +
        (metrics.get("follows", 0) * 5) +
        (metrics.get("shares", 0) * 2)
    ) / views * 1000
 
    text = (f"Platform: {video_data.get('platform')} "
            f"Niche: {video_data.get('niche')} "
            f"Type: {video_data.get('content_type')} "
            f"Prompt: {video_data.get('prompt', '')[:200]}")
 
    video_id = f"{video_data.get('platform')}_{video_data.get('account')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
 
    index.upsert(vectors=[{
        "id": video_id,
        "values": embed_text(text),
        "metadata": {
    "prompt": (video_data.get("prompt") or "")[:500],
    "caption": (video_data.get("caption") or "")[:200],
    "platform": video_data.get("platform") or "",
    "account": video_data.get("account") or "",
    "niche": video_data.get("niche") or "general",
    "content_type": video_data.get("content_type") or "",
    "conversion_score": conversion_score,
    "views": metrics.get("views") or 0,
    "posted_at": video_data.get("posted_at") or datetime.utcnow().isoformat(),
}
    }])

    print(f"Stored video memory: {video_id} (conversion_score: {conversion_score:.2f})")

def get_best_performing_content(niche: str,
    content_type: str = None,
    platform: str = None,
    top_k: int = 5
) -> list[dict]:
    if not PINECONE_AVAILABLE:
        return []
    
    query_text = f"""
    High converting content for {niche} creators on {platform or 'social media'}.
    Content type: {content_type or 'tutorial or product-led'}.
    Magic Hour AI video creation tool.
    Natural feeling, not robotic, product showcase.
    """

    query_vector = embed_text(query_text)

    filter_dict = {"niche": {"$in": [niche, "general"]}}
    if platform:
        filter_dict["platform"] = platform
    if content_type:
        filter_dict["content_type"] = content_type

    try:
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )

        matches = results.get("matches", [])
        matches.sort(key=lambda x:x.get("metadata", {}).get("conversion_score", 0), reverse=True)

        winners = []
        for match in matches:
            meta = match.get("metadata", {})
            winners.append({
                "prompt": meta.get("prompt"),
                "caption": meta.get("caption"),
                "conversion_score": meta.get("conversion_score"),
                "views": meta.get("views"),
                "content_type": meta.get("content_type"),
                "niche": meta.get("niche"),
            })

        print(f"Retrieves {len(winners)} relevant memories for {niche}/{platform}")
        return winners
        
    except Exception as e:
        print(f"Memoru retreival error: {e}")
        return []
    
def get_memory_stats() -> dict:
    if not PINECONE_AVAILABLE:
        return {"status": "not configured"}
    
    stats = index.describe_index_stats()
    return {
        "total_videos_stores": stats.get("total_vector_count", 0),
        "index_name": INDEX_NAME,
        "status": "active"
    }

if __name__ == "__main__":
    print("Memory module loaded.")
    print(f"Pinecone available :{PINECONE_AVAILABLE}")
    print(f"Stats: {get_memory_stats()}")