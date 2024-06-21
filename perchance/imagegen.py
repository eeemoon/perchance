import aiohttp
import asyncio
import io
import random
from playwright.async_api import async_playwright, Request
from typing import Literal

from . import errors
from .generator import Generator
from .utils import timeout


class ImageGenerator(Generator):
    BASE_URL = "https://image-generation.perchance.org/api"

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
                            nonlocal key

                            resp = await request.response()
                            data = await resp.json()

                            key = data['userKey']
                        except Exception:
                            pass

                page.on("request", on_request)

                await page.goto("https://perchance.org/ai-text-to-image-generator")

                iframe_element = await page.query_selector('xpath=//iframe[@src]')
                frame = await iframe_element.content_frame()

                await frame.click('xpath=//button[@id="generateButtonEl"]')

                async with timeout(8.0, errors.ConnectionError) as t:
                    while not key:
                        await t.tick()
                        await asyncio.sleep(0.1)

                await browser.close()

                return key
        except Exception:
            raise errors.ConnectionError()

    async def image(
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
            Accuracy of the prompt in range `1-30`. 
        """
        await self.refresh()

        try:
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
                async with timeout(12.0, errors.ConnectionError) as t:
                    while image_id is None:
                        await t.tick()
                        
                        async with session.post(
                            ImageGenerator.BASE_URL + '/generate',
                            params={
                                'prompt': prompt,
                                'negativePrompt': negative_prompt or '',
                                'userKey': self._key,
                                '__cache_bust': random.random(),
                                'seed': seed,
                                'resolution': resolution,
                                'guidanceScale': guidance_scale,
                                'channel': 'ai-text-to-image-generator',
                                'subChannel': 'public',
                                'requestId': random.random()
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
                    ImageGenerator.BASE_URL + '/downloadTemporaryImage',
                    params={
                        'imageId': image_id
                    }
                ) as response:
                    image = io.BytesIO(await response.content.read())
                    image.seek(0)
                    return image    
        except Exception:
            raise errors.ConnectionError()