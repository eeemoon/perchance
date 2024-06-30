# perchance
[![pypi](https://img.shields.io/pypi/v/perchance)](https://pypi.org/project/perchance)
[![python](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads)
[![CodeFactor](https://www.codefactor.io/repository/github/eeemoon/perchance/badge)](https://www.codefactor.io/repository/github/eeemoon/perchance)
[![BuyMeACoffee](https://img.shields.io/badge/support-yellow)](https://www.buymeacoffee.com/eeemoon)

Unofficial Python API for [Perchance](https://perchance.org).

## Installation
To install this module, run the following command:
```
pip install perchance
```

## Examples
### Text generation
```python
import asyncio
import perchance

async def main():
    gen = perchance.TextGenerator()
    prompt = "How far is the moon?"

    async for chunk in gen.text(prompt):
        print(chunk, end='')

asyncio.run(main())
```
### Image generation
```python
import asyncio
import perchance
from PIL import Image

async def main():
    gen = perchance.ImageGenerator()
    prompt = "Fantasy landscape"

    async with await gen.image(prompt) as result:
        binary = await result.download()
        image = Image.open(binary)
        image.show()

asyncio.run(main())
```