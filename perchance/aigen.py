import aiohttp
import random


class AIGenerator:
    BASE_URL: str

    def __init__(self) -> None:
        self._key: str | None = None

    @classmethod
    async def _fetch_key(cls) -> str:
        """Fetch an user key from the website."""
        raise NotImplementedError()
    
    @classmethod
    async def _verify_key(cls, key: str) -> bool:
        """Verify an user key."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    cls.BASE_URL + '/checkVerificationStatus',
                    params={
                        'userKey': key,
                        '__cacheBust': random.random()
                    }
                ) as response:
                    return 'not_verified' not in await response.text()
        except Exception:
            return False
            
    async def refresh(self) -> None:
        """Verify and refresh the user key if needed."""
        cls = type(self)
        if not self._key or not await cls._verify_key(self._key):
            self._key = await cls._fetch_key()
