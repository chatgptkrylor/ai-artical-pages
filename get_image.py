#!/usr/bin/env python3
"""
Runware image fetcher for Scribe agent.
Usage: python3 get_image.py "your prompt here"
Returns: image URL on stdout
"""
import sys
import os
import asyncio
import httpx
import uuid

RUNWARE_API_KEY = os.environ.get("RUNWARE_API_KEY", "8Zd5FA3PfTWgP0GVg09GiiGzt1kfBTSv")

async def get_image(prompt: str) -> str:
    if not RUNWARE_API_KEY:
        print("ERROR: RUNWARE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    async with httpx.AsyncClient(timeout=30) as client:
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
        return data["data"][0]["imageURL"]

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "professional workspace desk"
    url = asyncio.run(get_image(prompt))
    print(url)
