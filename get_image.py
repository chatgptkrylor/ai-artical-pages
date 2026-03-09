
"""
Image fetcher for Scribe agent.
Usage: python3 get_image.py "your prompt here"
Returns: relative image path on stdout (saved locally)

Pipeline:
  1. Runware AI (2 retries)
  2. Pexels stock photos (fallback)
  3. SVG placeholder (last resort)
"""
import sys
import os
import asyncio
import httpx
import uuid
import hashlib
import random
from datetime import datetime

RUNWARE_API_KEY = "8Zd5FA3PfTWgP0GVg09GiiGzt1kfBTSv"
PEXELS_API_KEY = "8itc8brvysUGcFtxT8A3IBTDygeOBQsVzo8JMK9kzdtXacIBofrYfv2x"
IMAGE_DIR = "/home/krylorix/Documents/ai-article-pages/images"
MAX_RETRIES = 2
RETRY_DELAY = 3


async def fetch_from_runware(client: httpx.AsyncClient, prompt: str) -> str:
    """Call Runware API and return the image URL."""
    resp = await client.post(
        "https://api.runware.ai/v1",
        json=[{
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "positivePrompt": prompt,
            "model": "runware:108@1",
            "width": 1024,
            "height": 576,
            "numberResults": 1,
            "outputFormat": "WEBP",
        }],
        headers={
            "Authorization": f"Bearer {RUNWARE_API_KEY}",
            "Content-Type": "application/json",
        }
    )
    data = resp.json()
    if "data" not in data or len(data["data"]) == 0:
        raise ValueError(f"No image data in response: {data}")
    return data["data"][0]["imageURL"]


async def fetch_from_pexels(client: httpx.AsyncClient, prompt: str) -> str:
    """Search Pexels for a relevant landscape photo and return its URL."""
    search_query = " ".join(prompt.split()[:5])

    resp = await client.get(
        "https://api.pexels.com/v1/search",
        params={
            "query": search_query,
            "orientation": "landscape",
            "size": "medium",
            "per_page": 10,
        },
        headers={
            "Authorization": PEXELS_API_KEY,
        }
    )

    if resp.status_code != 200:
        raise ValueError(f"Pexels API returned {resp.status_code}")

    data = resp.json()
    photos = data.get("photos", [])

    if not photos:
        broad_query = " ".join(prompt.split()[:2])
        resp = await client.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": broad_query,
                "orientation": "landscape",
                "size": "medium",
                "per_page": 10,
            },
            headers={
                "Authorization": PEXELS_API_KEY,
            }
        )
        data = resp.json()
        photos = data.get("photos", [])

    if not photos:
        raise ValueError("No photos found on Pexels")

    photo = random.choice(photos)
    image_url = photo["src"]["landscape"]
    photographer = photo.get("photographer", "Unknown")
    photo_url = photo.get("url", "")

    print(f"Pexels: Photo by {photographer} — {photo_url}", file=sys.stderr)

    return image_url


async def download_image(client: httpx.AsyncClient, url: str, filepath: str) -> str:
    """Download image from URL and save to filepath."""
    resp = await client.get(url)
    if resp.status_code != 200:
        raise ValueError(f"Download failed with status {resp.status_code}")

    content_type = resp.headers.get("content-type", "")
    if "jpeg" in content_type or "jpg" in content_type:
        if not filepath.endswith(".jpg"):
            filepath = filepath.rsplit(".", 1)[0] + ".jpg"
    elif "png" in content_type:
        if not filepath.endswith(".png"):
            filepath = filepath.rsplit(".", 1)[0] + ".png"

    with open(filepath, "wb") as f:
        f.write(resp.content)
    return filepath


def generate_placeholder(prompt: str, filepath: str) -> str:
    """Generate a simple SVG placeholder when all image sources fail."""
    label = prompt[:40].strip()
    if len(prompt) > 40:
        label += "..."

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="576" viewBox="0 0 1024 576">
  <rect width="1024" height="576" fill="#1a1a2e"/>
  <rect x="2" y="2" width="1020" height="572" fill="none" stroke="#e85d26" stroke-width="1" stroke-dasharray="8,4" rx="10"/>
  <circle cx="512" cy="240" r="48" fill="none" stroke="#3a3a5c" stroke-width="2"/>
  <path d="M492 240 L520 220 L520 260Z" fill="#3a3a5c"/>
  <text x="512" y="330" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#5a5a7a">{label}</text>
  <text x="512" y="360" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#3a3a5c">Image unavailable</text>
</svg>'''

    svg_path = filepath.rsplit(".", 1)[0] + ".svg"
    with open(svg_path, "w") as f:
        f.write(svg)
    return svg_path


async def get_image(prompt: str) -> str:
    if not RUNWARE_API_KEY or RUNWARE_API_KEY == "YOUR_RUNWARE_KEY_HERE":
        print("WARNING: RUNWARE_API_KEY not set, skipping to Pexels", file=sys.stderr)

    os.makedirs(IMAGE_DIR, exist_ok=True)

    slug = hashlib.md5(prompt.encode()).hexdigest()[:10]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    base_filename = f"{slug}-{timestamp}"
    filepath = os.path.join(IMAGE_DIR, f"{base_filename}.webp")

    async with httpx.AsyncClient(timeout=30) as client:

        # === STAGE 1: Runware with retries ===
        if RUNWARE_API_KEY and RUNWARE_API_KEY != "YOUR_RUNWARE_KEY_HERE":
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    print(f"[Runware] Attempt {attempt}/{MAX_RETRIES}...", file=sys.stderr)
                    image_url = await fetch_from_runware(client, prompt)
                    saved_path = await download_image(client, image_url, filepath)
                    final_name = os.path.basename(saved_path)
                    print(f"[Runware] Success: {final_name}", file=sys.stderr)
                    return f"../images/{final_name}"
                except Exception as e:
                    print(f"[Runware] Attempt {attempt} failed: {e}", file=sys.stderr)
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY)

            # Retry with simplified prompt
            try:
                print("[Runware] Trying simplified prompt...", file=sys.stderr)
                simple_prompt = prompt.split(",")[0].strip() + ", professional photo"
                image_url = await fetch_from_runware(client, simple_prompt)
                saved_path = await download_image(client, image_url, filepath)
                final_name = os.path.basename(saved_path)
                print(f"[Runware] Simplified success: {final_name}", file=sys.stderr)
                return f"../images/{final_name}"
            except Exception as e:
                print(f"[Runware] Simplified also failed: {e}", file=sys.stderr)

        # === STAGE 2: Pexels fallback ===
        if PEXELS_API_KEY and PEXELS_API_KEY != "YOUR_PEXELS_KEY_HERE":
            try:
                print(f"[Pexels] Searching for: {prompt[:50]}...", file=sys.stderr)
                pexels_filepath = os.path.join(IMAGE_DIR, f"{base_filename}.jpg")
                image_url = await fetch_from_pexels(client, prompt)
                saved_path = await download_image(client, image_url, pexels_filepath)
                final_name = os.path.basename(saved_path)
                print(f"[Pexels] Success: {final_name}", file=sys.stderr)
                return f"../images/{final_name}"
            except Exception as e:
                print(f"[Pexels] Failed: {e}", file=sys.stderr)

            # Try broader Pexels search
            try:
                print("[Pexels] Trying broader search...", file=sys.stderr)
                fallback_queries = [
                    "email marketing office",
                    "laptop workspace professional",
                    "business technology computer",
                    "office desk modern",
                    "digital marketing team",
                ]
                broad_query = random.choice(fallback_queries)
                pexels_filepath = os.path.join(IMAGE_DIR, f"{base_filename}-broad.jpg")
                image_url = await fetch_from_pexels(client, broad_query)
                saved_path = await download_image(client, image_url, pexels_filepath)
                final_name = os.path.basename(saved_path)
                print(f"[Pexels] Broad search success: {final_name}", file=sys.stderr)
                return f"../images/{final_name}"
            except Exception as e:
                print(f"[Pexels] Broad search also failed: {e}", file=sys.stderr)

        # === STAGE 3: SVG placeholder (last resort) ===
        print("[Placeholder] Generating SVG fallback...", file=sys.stderr)
        svg_path = generate_placeholder(prompt, filepath)
        svg_filename = os.path.basename(svg_path)
        print(f"[Placeholder] Saved: {svg_filename}", file=sys.stderr)
        return f"../images/{svg_filename}"


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "professional workspace desk"
    path = asyncio.run(get_image(prompt))
    print(path)