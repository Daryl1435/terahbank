"""
Quick Twilio SMS test — sends a real SMS to your verified number.
Run: python scripts/test_sms.py
"""
import asyncio
from base64 import b64encode
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from core.config import settings

TO_NUMBER = "+237675642835"  # your verified Twilio caller ID


async def main() -> None:
    print(f"Account SID : {settings.TWILIO_ACCOUNT_SID}")
    print(f"From        : {settings.TWILIO_PHONE_NUMBER}")
    print(f"To          : {TO_NUMBER}")
    print()

    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print("ERROR: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN not set in .env")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    auth = b64encode(
        f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode()
    ).decode()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Basic {auth}"},
            data={
                "From": settings.TWILIO_PHONE_NUMBER,
                "To": TO_NUMBER,
                "Body": "TerahBank test: votre SMS Twilio fonctionne correctement. Ne pas repondre.",
            },
        )

    if resp.status_code == 201:
        sid = resp.json().get("sid", "")
        print(f"SUCCESS — SMS sent! SID: {sid}")
        print("Check your phone for the message.")
    else:
        print(f"FAILED — HTTP {resp.status_code}")
        print(resp.text)


asyncio.run(main())
