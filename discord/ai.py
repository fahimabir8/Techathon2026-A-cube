import aiohttp
import json
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("AI_API")
MODEL_INTENT = os.getenv("AI_MODEL_INTENT")
MODEL_RESPOND = os.getenv("AI_MODEL_RESPOND")


class AiHandler:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def query(self, payload):
        assert isinstance(URL, str)
        async with self.session.post(URL, json=payload) as resp:
            resp.raise_for_status()
            r = await resp.json()
            r = r["choices"][0]["message"]["content"]
            print("ai output:", r)
            print(type(r))
            return r

    async def get_intent(self, prompt: str):
        payload = {
            "model": MODEL_INTENT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        return await self.query(payload)

    async def humanize(self, cmd, data):
        payload = {
            "model": MODEL_RESPOND,
            "messages": [{"role": "user", "content": f"{cmd} {json.dumps(data)}"}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        print("running query: ", payload)
        return await self.query(payload)
