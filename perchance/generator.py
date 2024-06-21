import aiohttp
import random

from . import errors


class Generator:
    BASE_URL: str

    def __init__(self):
        self._key: str | None = None

    @classmethod
    async def _fetch_key(cls) -> str:
        raise NotImplementedError()
    
    @classmethod
    async def _verify_key(cls, key: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    cls.BASE_URL + '/checkVerificationStatus',
                    params={
                        'userKey': key,
                        '__cacheBust': str(random.random())
                    }
                ) as response:
                    return 'not_verified' not in await response.text()
        except Exception:
            raise errors.ConnectionError()
            
    async def refresh(self) -> None:
        """Refresh auth key from the website."""
        cls = type(self)
        if not self._key or not await cls._verify_key(self._key):
            self._key = await cls._fetch_key()
