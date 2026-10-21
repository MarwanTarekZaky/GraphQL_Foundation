import asyncio 

from app.database import user_collection


async def main():
    
    await user_collection.delete_many({})
    
    await user_collection.insert_many([
    {
        "id": 1,
        "fullName": "Marwan Tarek Zaky",
        "nickname": "Marwan",
        "email": "marwan@example.com",
        "role": "admin",
        "token": "marwan-secret-token",
    },
    {
        "id": 2,
        "fullName": "Leia Organa",
        "nickname": "Leia",
        "email": "leia@example.com",
        "role": "user",
        "token": "leia-secret-token",
    },
    ])

    
    print("Database seeded successfully.")
    print("Full name: Marwan Tarek Zaky")
    print("Nickname: Marwan")
    

asyncio.run(main())