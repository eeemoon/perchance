import aiohttp
import asyncio
import random
import json
from typing import AsyncGenerator
from playwright.async_api import async_playwright, Request

from . import errors
from .generator import Generator
from .utils import timeout


class TextGenerator(Generator):
    BASE_URL = "https://text-generation.perchance.org/api"

    @classmethod
    async def _fetch_key(cls) -> str:
        try:
            key: str | None = None

            async with async_playwright() as pw:
                browser = await pw.firefox.launch(headless=True)
                page = await browser.new_page()

                async def on_request(request: Request):
                    if request.url.startswith(cls.BASE_URL + '/verifyUser'):
                        try:
                            resp = await request.response()
                            data = await resp.json()

                            nonlocal key
                            key = data['userKey']
                        except Exception:
                            pass

                page.on("request", on_request)

                await page.goto("https://perchance.org/ai-text-generator")

                iframe_element = await page.query_selector('xpath=//iframe[@src]')
                frame = await iframe_element.content_frame()

                await frame.click('xpath=//button[@id="generateBtn"]')

                async with timeout(8.0, errors.ConnectionError) as t:
                    while not key:
                        await t.tick()
                        await asyncio.sleep(0.1)

                await frame.click('xpath=//button[@id="stopBtn"]')

                await browser.close()

            return key
        except Exception:
            raise errors.ConnectionError()

    async def text(
        self,
        prompt: str,
        *,
        start_with: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate text.

        Parameters
        ----------
        prompt: `str`
            Text instruction.
        start_with: `str` | `None`
            Text to start with.
        """
        await self.refresh()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TextGenerator.BASE_URL + '/generate',
                    params={
                        'userKey': self._key,
                        '__cacheBust': random.random(),
                        'requestId': f"aiTextCompletion{random.randint(0, 2**30)}"
                    },
                    json={
                        'generatorName': 'ai-text-generator',
                        'instruction': prompt,
                        'instructionTokenCount': 1,
                        'startWith': start_with or '',
                        'startWithTokenCount': 1,
                        'stopSequences': []
                    }
                ) as response:
                    
                    if not response.ok:
                        body = await response.json(content_type=None)
                        status = body['status']
                        print(body, response.status)

                        if status == 'invalid_key':
                            raise errors.AuthError()
                        elif status == 'invalid_data':
                            raise errors.BadRequestError()
                    
                    async for data_chunk in response.content.iter_any():
                        for line in data_chunk.decode().split('\n\n'):
                            if len(line) == 0:
                                continue

                            data = json.loads(line[5:])
                            yield data['text']
        except Exception:
            raise errors.ConnectionError()
                            