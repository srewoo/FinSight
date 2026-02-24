import asyncio
from httpx import AsyncClient

async def run_test():
    async with AsyncClient(base_url="http://localhost:8001/api") as ac:
        # Create user
        print("Provisioning admin1@example.com...")
        resp = await ac.post("/admin/provision-user", json={
            "email": "admin1@example.com",
            "password": "SecurePassword123!",
            "name": "Super Admin"
        })
        print(resp.status_code, resp.text)
        
        # Login
        print("Logging in...")
        resp = await ac.post("/auth/token", data={
            "username": "admin1@example.com",
            "password": "SecurePassword123!"
        })
        print(resp.status_code, resp.text)
        
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            # Test protected route
            print("Accessing protected profile...")
            profile_resp = await ac.get("/user/profile", headers={"Authorization": f"Bearer {token}"})
            print(profile_resp.status_code, profile_resp.text)

asyncio.run(run_test())
