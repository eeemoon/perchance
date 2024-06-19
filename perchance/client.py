import aiohttp
import asyncio
import io
import random
import re
from playwright.async_api import async_playwright, Request
from typing import Literal


class Client:
    BASE_URL = "https://image-generation.perchance.org/api"

    def __init__(self):
        self._key: str | None = None

    async def _fetch_key(self) -> str:
        urls: list[str] = []

        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()

            def on_request(request: Request):
                urls.append(request.url)

            page.on("request", on_request)

            await page.goto("https://perchance.org/ai-text-to-image-generator")

            iframe_element = await page.query_selector('xpath=//iframe[@src]')
            frame = await iframe_element.content_frame()
            await frame.click('xpath=//button[@id="generateButtonEl"]')

            key = None
            while key is None:
                pattern = r"userKey=([a-f\d]{64})"
                keys = re.findall(pattern, ''.join(urls))
                if keys:
                    key = keys[0]

                urls = []

                await asyncio.sleep(0.5)

            await browser.close()

        return key

    async def _verify_key(self, key: str) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                Client.BASE_URL + '/checkVerificationStatus',
                params={
                    'userKey': key,
                    '__cacheBust': str(random.random())
                }
            ) as response:
                return 'not_verified' not in await response.text()
            
    async def refresh(self) -> None:
        """Refresh auth key from the website."""
        if not self._key or not await self._verify_key(self._key):
            self._key = await self._fetch_key()

    async def generate_image(
        self,
        prompt: str,
        *,
        negative_prompt: str | None = None,
        seed: int = -1,
        shape: Literal['portrait', 'square', 'landscape'] = 'square',
        guidance_scale: float = 7.0
    ) -> io.BytesIO:
        """
        Generate image.

        Parameters
        ----------
        prompt: `str`
            Image description.
        negative_prompt: `str` | `None`
            Things you do NOT want to see in the image.
        seed: `int`
            Generation seed.
        shape: `str`
            Image shape. Can be either `portrait`, `square` or `landscape`.
        guidance_scale: `float`
            Accuracy of the prompt in range `7-20`. 
        """
        await self.refresh()

        image_id: str | None = None

        if shape == 'portrait':
            resolution = '512x768'
        elif shape == 'square':
            resolution = '512x512'
        elif shape == 'landscape':
            resolution = '768x512'
        else:
            raise ValueError(f"Invalid shape: {shape}")

        async with aiohttp.ClientSession() as session:
            while image_id is None:
                async with session.get(
                    Client.BASE_URL + '/generate',
                    params={
                        'prompt': prompt,
                        'negativePrompt': negative_prompt or '',
                        'userKey': self._key,
                        '__cache_bust': str(random.random()),
                        'seed': str(seed),
                        'resolution': resolution,
                        'guidanceScale': str(guidance_scale),
                        'channel': 'ai-text-to-image-generator',
                        'subChannel': 'public',
                        'requestId': str(random.random())
                    }
                ) as response:
                    if 'invalid_key' in await response.text():
                        raise ValueError("Invalid key")

                    data = await response.json(content_type=None)
                    try:
                        image_id = data['imageId']
                    except KeyError:
                        await asyncio.sleep(4.0)

            async with session.get(
                Client.BASE_URL + '/downloadTemporaryImage',
                params={
                    'imageId': image_id
                }
            ) as response:
                image = io.BytesIO(await response.content.read())
                image.seek(0)
                return image