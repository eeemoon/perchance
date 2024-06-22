import asyncio
import perchance
from PIL import Image


async def main():
    print('Initializing...')
    
    gen = perchance.ImageGenerator()
    # refresh generator so it will take less
    # time to generate the first response
    await gen.refresh()
    
    while True:
        prompt = input("Prompt: ")
        print("Generating...")

        async with await gen.image(prompt) as res:
            # download image as a bytes-like object
            raw = await res.download()
            # open the image with Pillow
            img = Image.open(raw)

            print(f"Result: {res}")
            img.show()


if __name__ == '__main__':
    asyncio.run(main())