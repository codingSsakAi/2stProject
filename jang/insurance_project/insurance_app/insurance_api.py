import httpx, json, asyncio
from django.conf import settings

CODEF_BASE_URL = "https://api.codef.io"

async def get_codef_token():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CODEF_BASE_URL}/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(settings.CODEF_CLIENT_ID, settings.CODEF_CLIENT_SECRET)
        )
        return resp.json()["access_token"]

async def fetch_insurance_premium(user, coverage_options):
    token = await get_codef_token()
    payload = {
        "birthDate": user.birth_date.strftime("%Y%m%d"),
        "gender": "M" if user.gender == "남성" else "F",
        "licenseIssueDate": user.license_date.strftime("%Y%m%d"),
        "carModel": user.car_model_code,
        "coverage": {"대인배상": "무제한", "대물배상": "2억원", "자기차량손해": True},
        "specialTerms": coverage_options,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CODEF_BASE_URL}/v1/insurance/car/premium",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            data=json.dumps(payload)
        )
        return resp.json()
