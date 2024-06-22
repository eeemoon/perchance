import aiofiles
import aiohttp
import asyncio
import io
import random
from playwright.async_api import async_playwright, Request
from typing import Literal

from . import errors
from .aigen import AIGenerator
from .utils import timeout


class ImageResponse:
    def __init__(
        self, 
        *, 
        generator: "ImageGenerator",
        image_id: str,
        file_ext: str,
        seed: int,
        prompt: str,
        width: int,
        height: int,
        guidance_scale: float,
        negative_prompt: str | None,
        maybe_nsfw: bool
    ):
        self._generator: ImageGenerator = generator
        self._raw_image: io.BytesIO | None = None

        self.image_id: str = image_id
        self.file_ext: str = file_ext
        self.seed: int = seed
        self.prompt: str = prompt
        self.width: int = width
        self.height: int = height
        self.guidance_scale: float = guidance_scale
        self.negative_prompt: str | None = negative_prompt
        self.maybe_nsfw: bool = maybe_nsfw
    
    def __str__(self) -> str:
        return f"{self.image_id}.{self.file_ext}"
    
    async def __aenter__(self) -> "ImageResponse":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._raw_image:
            self._raw_image.close()

    @property
    def size(self) -> tuple[int, int]:
        """Size of the image."""
        return self.width, self.height

    async def download(self) -> io.BytesIO:
        """Download the image."""
        if self._raw_image is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    ImageGenerator.BASE_URL + '/downloadTemporaryImage',
                    params={
                        'imageId': self.image_id
                    }
                ) as response:
                    try:
                        raw = await response.content.read()
                        image = io.BytesIO(raw)
                        image.seek(0)
                        self._raw_image = image
                    except Exception:
                        raise errors.ConnectionError()
                    
        return self._raw_image
                
    async def save(self, filename: str | None = None) -> None:
        """
        Download and save the image.

        Parameters
        ----------
        filename: `str` | `None`
            Name of the output file.
        """
        file = filename or f"{self.image_id}.{self.file_ext}" 

        async with aiofiles.open(file, 'wb') as f:
            img = await self.download()
            await f.write(img.read())
            

class ImageGenerator(AIGenerator):
    """
    AI image generator.

    Example usage
    -------------
    ```python
    gen = ImageGenerator()
    prompt = "A cat sitting on stairs"

    async with await gen.image(prompt) as result:
        raw = await result.download()
        image = Image.open(raw)
        image.show()
    ```
    """

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

                async with timeout(20.0, errors.ConnectionError) as t:
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
    ) -> ImageResponse:
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
            async with timeout(20.0, errors.ConnectionError) as t:
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
                        try:
                            body = await response.json(content_type=None)
                            status = body['status']
                        except Exception:
                            raise errors.ConnectionError()

                        if status == 'invalid_key':
                            raise errors.AuthError()
                        elif status == 'invalid_data':
                            raise errors.BadRequestError()
                        elif status != 'success':
                            await asyncio.sleep(4.0)
                            continue
                
                        return ImageResponse(
                            generator=self,
                            image_id=body['imageId'],
                            file_ext=body['fileExtension'],
                            seed=seed,
                            prompt=prompt,
                            width=body['width'],
                            height=body['height'],
                            guidance_scale=guidance_scale,
                            negative_prompt=negative_prompt,
                            maybe_nsfw=body['maybeNsfw']
                        )
                        