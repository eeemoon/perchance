import asyncio
import perchance


async def main():
    print('Starting text generator...', end='')
    
    gen = perchance.TextGenerator()
    # refresh generator so it will take less
    # time to generate the first response
    await gen.refresh()
    
    while True:
        print('\n---------------')
        prompt = input("Prompt: ")
       
        print("Result: ", end='')
        async for chunk in gen.text(prompt):
            # print text as soon as it generated
            print(chunk, end='') 


if __name__ == '__main__':
    asyncio.run(main())