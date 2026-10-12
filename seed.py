import asyncio 

from app.database import user_collection


async def main():
    
    await user_collection.delete_many({})
    
    await user_collection.insert_one({
        "id": 1,
        "fullName": "Marwan Tarek Zaky",
        "nickname": "Marwan",
        "token": "marwan-secret-token",
    })
    
    print("Database seeded successfully.")
    print("Full name: Marwan Tarek Zaky")
    print("Nickname: Marwan")
    

asyncio.run(main())