# app/payments.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx

from .settings import get_settings, Settings

router = APIRouter(prefix="/payments", tags=["payments"])

class InitializeRequest(BaseModel):
    course_id: Optional[str] = None
    email: Optional[EmailStr] = None
    amount: Optional[int] = None   # amount in NGN (not kobo). Optional if you lookup course price.

async def get_course_amount(course_id: str) -> int:
    """
    Replace this with your DB lookup to fetch course.price (NGN).
    Return price in NGN (integer). For example: 2000
    """
    # Example stub:
    course_map = {"course_1": 2000, "course_2": 3500}
    return course_map.get(course_id, 0)

@router.post("/initialize")
async def initialize_payment(payload: InitializeRequest, settings: Settings = Depends(get_settings)):
    # Determine amount (in NGN)
    amount_ngn = payload.amount
    if not amount_ngn:
        if payload.course_id:
            amount_ngn = await get_course_amount(payload.course_id)
        else:
            raise HTTPException(status_code=400, detail="Missing amount or course_id")

    if amount_ngn <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    email = payload.email or "customer@example.com"

    # Paystack requires amount in kobo
    amount_kobo = int(amount_ngn) * 100

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "email": email,
        "amount": amount_kobo,
        "callback_url": settings.CALLBACK_URL
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{settings.PAYSTACK_API_URL}/transaction/initialize",
                                 json=body, headers=headers)

    if resp.status_code not in (200, 201):
        # pass through Paystack error so frontend can see it
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()   # returns Paystack response (status, message, data.authorization_url, data.reference,...)

@router.get("/verify/{reference}")
async def verify_payment(reference: str, settings: Settings = Depends(get_settings)):
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{settings.PAYSTACK_API_URL}/transaction/verify/{reference}",
                                headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()
