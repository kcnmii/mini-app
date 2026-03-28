import asyncio
import base64
import httpx

async def test():
    base_url = "https://sigex.kz"
    
    # Register
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base_url}/api/egovQr", json={"description": "Test"})
        resp.raise_for_status()
        reg = resp.json()
        print("Registration OK:", reg)
        
        # Send data
        data_url = reg["dataURL"]
        payload = {
            "signMethod": "CMS_SIGN_ONLY",
            "documentsToSign": [
                {
                    "id": 1,
                    "nameRu": "Test",
                    "meta": [],
                    "document": {
                        "file": {
                            "mime": "",
                            "data": base64.b64encode(b"Hello World").decode("ascii")
                        }
                    }
                }
            ]
        }
        
        post_resp = await client.post(data_url, json=payload)
        print("Send Data Status:", post_resp.status_code)
        print("Send Data Text:", post_resp.text)

asyncio.run(test())
