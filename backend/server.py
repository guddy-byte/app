from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import hashlib
import jwt
import pdfplumber
import re
import base64
from io import BytesIO
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
JWT_SECRET = "your-secret-key-here"
JWT_ALGORITHM = "HS256"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    full_name: str
    phone: str
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str

class UserLogin(BaseModel):
    email: str
    password: str

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str
    options: List[str]
    correct_answer: int  # Index of correct option (0-based)

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    is_free: bool = True
    price: float = 0.0
    questions: List[Question] = []
    total_questions: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # Admin ID

class CourseCreate(BaseModel):
    title: str
    description: str
    is_free: bool = True
    price: float = 0.0

class TestAttempt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    course_id: str
    answers: Dict[str, int]  # question_id -> selected_option_index
    score: float
    total_questions: int
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    can_retake: bool = True

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    course_id: str
    amount: float
    currency: str = "NGN"
    status: str = "pending"  # pending, completed, failed
    paystack_reference: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Utility Functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def create_access_token(user_id: str, is_admin: bool = False) -> str:
    payload = {
        "user_id": user_id,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_doc = await db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user_doc)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# PDF Parser Function
def parse_pdf_to_questions(pdf_content: bytes) -> List[Question]:
    """Parse PDF content and extract questions"""
    questions = []
    
    try:
        # Read PDF from bytes
        pdf_file = BytesIO(pdf_content)
        
        with pdfplumber.open(pdf_file) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
        
        # Method 1: Try to parse structured format (like the sample)
        questions_method1 = parse_structured_format(text)
        if questions_method1:
            return questions_method1
        
        # Method 2: Try to parse simple Q&A format
        questions_method2 = parse_simple_format(text)
        if questions_method2:
            return questions_method2
        
        # Method 3: Try to parse numbered questions
        questions_method3 = parse_numbered_format(text)
        return questions_method3
        
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return []

def parse_structured_format(text: str) -> List[Question]:
    """Parse structured format like the GST104 sample"""
    questions = []
    
    # Split by question markers
    question_blocks = re.split(r'\n\d+\nQuestion\n', text)
    
    for i, block in enumerate(question_blocks[1:], 1):
        try:
            lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
            
            # Find question text
            question_text = ''
            options = []
            
            # Look for question text (after Mark line, before Select one)
            start_collecting = False
            for line in lines:
                if 'Mark' in line and 'out of' in line:
                    start_collecting = True
                    continue
                
                if start_collecting and line == 'Select one:':
                    break
                    
                if start_collecting and line:
                    question_text += line + ' '
            
            question_text = question_text.strip()
            
            # Extract options after "Select one:"
            collect_options = False
            for line in lines:
                if line == 'Select one:':
                    collect_options = True
                    continue
                
                if collect_options and line and not line.startswith('http://') and not line.startswith('4/'):
                    if len(options) < 4:
                        options.append(line)
            
            if question_text and len(options) >= 2:
                questions.append(Question(
                    question_text=question_text,
                    options=options[:4],  # Take max 4 options
                    correct_answer=0  # Default to first option, admin can adjust
                ))
                
        except Exception as e:
            continue
    
    return questions

def parse_simple_format(text: str) -> List[Question]:
    """Parse simple Q: A: format"""
    questions = []
    
    # Look for Q: or Question: patterns
    lines = text.split('\n')
    current_question = ''
    current_options = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for question markers
        if re.match(r'^Q\d*[:.]\s*', line) or re.match(r'^Question\s*\d*[:.]\s*', line, re.IGNORECASE):
            # Save previous question if exists
            if current_question and current_options:
                questions.append(Question(
                    question_text=current_question,
                    options=current_options[:4],
                    correct_answer=0
                ))
            
            # Start new question
            current_question = re.sub(r'^Q\d*[:.]\s*|^Question\s*\d*[:.]\s*', '', line, flags=re.IGNORECASE)
            current_options = []
            
        # Check for option markers
        elif re.match(r'^[A-D][.):]\s*', line):
            if current_question:
                option_text = re.sub(r'^[A-D][.):]\s*', '', line)
                current_options.append(option_text)
    
    # Don't forget the last question
    if current_question and current_options:
        questions.append(Question(
            question_text=current_question,
            options=current_options[:4],
            correct_answer=0
        ))
    
    return questions

def parse_numbered_format(text: str) -> List[Question]:
    """Parse numbered format (1. 2. 3.)"""
    questions = []
    
    # Split by numbered questions
    question_parts = re.split(r'\n(\d+\.)\s*', text)
    
    for i in range(1, len(question_parts), 2):
        if i + 1 < len(question_parts):
            question_content = question_parts[i + 1]
            
            lines = [line.strip() for line in question_content.split('\n') if line.strip()]
            
            if not lines:
                continue
                
            question_text = lines[0]
            options = []
            
            # Look for options in subsequent lines
            for line in lines[1:]:
                if re.match(r'^[A-D][.):]\s*', line):
                    option_text = re.sub(r'^[A-D][.):]\s*', '', line)
                    options.append(option_text)
                    if len(options) >= 4:
                        break
            
            if question_text and len(options) >= 2:
                questions.append(Question(
                    question_text=question_text,
                    options=options,
                    correct_answer=0
                ))
    
    return questions

# Routes

# Authentication Routes
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone
    )
    
    await db.users.insert_one(user.dict())
    
    # Create token
    token = create_access_token(user.id)
    
    return {
        "message": "Registration successful",
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    }

@api_router.post("/auth/login")
async def login(login_data: UserLogin):
    # Check for admin credentials
    if login_data.email == "Admin" and login_data.password == "Admin@01":
        # Check if admin exists
        admin_user = await db.users.find_one({"email": "admin@cbt.com"})
        if not admin_user:
            # Create admin user
            admin = User(
                email="admin@cbt.com",
                password_hash=hash_password("Admin@01"),
                full_name="System Administrator",
                phone="0000000000",
                is_admin=True
            )
            await db.users.insert_one(admin.dict())
            user_id = admin.id
            is_admin = True
        else:
            user_id = admin_user["id"]
            is_admin = True
    else:
        # Regular user login
        user_doc = await db.users.find_one({"email": login_data.email})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = User(**user_doc)
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user_id = user.id
        is_admin = user.is_admin
    
    token = create_access_token(user_id, is_admin)
    
    # Get user data for response
    user_doc = await db.users.find_one({"id": user_id})
    user = User(**user_doc)
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }
    }

# Course Management Routes
@api_router.post("/admin/courses/upload")
async def upload_course_pdf(
    title: str = Form(...),
    description: str = Form(...),
    is_free: bool = Form(True),
    price: float = Form(0.0),
    pdf_file: UploadFile = File(...),
    current_user: User = Depends(get_admin_user)
):
    # Read PDF content
    pdf_content = await pdf_file.read()
    
    # Parse questions from PDF
    questions = parse_pdf_to_questions(pdf_content)
    
    if not questions:
        raise HTTPException(status_code=400, detail="Could not extract questions from PDF")
    
    # Create course
    course = Course(
        title=title,
        description=description,
        is_free=is_free,
        price=price,
        questions=questions,
        total_questions=len(questions),
        created_by=current_user.id
    )
    
    await db.courses.insert_one(course.dict())
    
    return {
        "message": "Course created successfully",
        "course_id": course.id,
        "questions_extracted": len(questions)
    }

@api_router.get("/admin/courses")
async def get_admin_courses(current_user: User = Depends(get_admin_user)):
    courses = await db.courses.find().to_list(100)
    return [Course(**course) for course in courses]

@api_router.put("/admin/courses/{course_id}/questions/{question_id}")
async def update_question(
    course_id: str,
    question_id: str,
    question_data: Question,
    current_user: User = Depends(get_admin_user)
):
    # Find and update the specific question in the course
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Update the question
    for i, q in enumerate(course["questions"]):
        if q["id"] == question_id:
            course["questions"][i] = question_data.dict()
            break
    else:
        raise HTTPException(status_code=404, detail="Question not found")
    
    await db.courses.replace_one({"id": course_id}, course)
    
    return {"message": "Question updated successfully"}

# Public Course Routes
@api_router.get("/courses")
async def get_courses():
    courses = await db.courses.find({}, {"questions": 0}).to_list(100)  # Exclude questions
    return [
        {
            "id": course["id"],
            "title": course["title"],
            "description": course["description"],
            "is_free": course["is_free"],
            "price": course["price"],
            "total_questions": course["total_questions"],
            "created_at": course["created_at"]
        }
        for course in courses
    ]

@api_router.get("/courses/{course_id}")
async def get_course_details(course_id: str, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user can access this course
    if not course["is_free"]:
        # Check if user has paid
        payment = await db.payments.find_one({
            "user_id": current_user.id,
            "course_id": course_id,
            "status": "completed"
        })
        if not payment:
            raise HTTPException(status_code=403, detail="Payment required to access this course")
    
    # Return course with questions but without correct answers
    course_data = Course(**course)
    
    # Remove correct answers from questions
    questions_without_answers = []
    for q in course_data.questions:
        questions_without_answers.append({
            "id": q.id,
            "question_text": q.question_text,
            "options": q.options
        })
    
    return {
        "id": course_data.id,
        "title": course_data.title,
        "description": course_data.description,
        "total_questions": course_data.total_questions,
        "questions": questions_without_answers
    }

# Test Taking Routes
@api_router.post("/courses/{course_id}/attempt")
async def submit_test_attempt(
    course_id: str,
    answers: Dict[str, int],
    current_user: User = Depends(get_current_user)
):
    # Get course
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course_obj = Course(**course)
    
    # Check if user can access this course
    if not course_obj.is_free:
        payment = await db.payments.find_one({
            "user_id": current_user.id,
            "course_id": course_id,
            "status": "completed"
        })
        if not payment:
            raise HTTPException(status_code=403, detail="Payment required")
    
    # Check if user has already attempted this course (for paid courses)
    if not course_obj.is_free:
        existing_attempt = await db.test_attempts.find_one({
            "user_id": current_user.id,
            "course_id": course_id
        })
        if existing_attempt:
            raise HTTPException(status_code=400, detail="You have already attempted this course. Payment required for retake.")
    
    # Calculate score
    correct_answers = 0
    total_questions = len(course_obj.questions)
    
    for question in course_obj.questions:
        if question.id in answers:
            if answers[question.id] == question.correct_answer:
                correct_answers += 1
    
    # Calculate score out of 100
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # Save attempt
    attempt = TestAttempt(
        user_id=current_user.id,
        course_id=course_id,
        answers=answers,
        score=score,
        total_questions=total_questions,
        can_retake=course_obj.is_free
    )
    
    await db.test_attempts.insert_one(attempt.dict())
    
    return {
        "message": "Test completed successfully",
        "score": score,
        "correct_answers": correct_answers,
        "total_questions": total_questions,
        "percentage": f"{score:.1f}%"
    }

@api_router.get("/my-attempts")
async def get_user_attempts(current_user: User = Depends(get_current_user)):
    attempts = await db.test_attempts.find({"user_id": current_user.id}).to_list(100)
    
    # Get course details for each attempt
    result = []
    for attempt in attempts:
        course = await db.courses.find_one({"id": attempt["course_id"]})
        if course:
            result.append({
                "id": attempt["id"],
                "course_title": course["title"],
                "score": attempt["score"],
                "total_questions": attempt["total_questions"],
                "completed_at": attempt["completed_at"],
                "can_retake": attempt["can_retake"]
            })
    
    return result

# Payment Routes (Paystack Integration)
@api_router.post("/payments/initialize")
async def initialize_payment(
    course_id: str,
    current_user: User = Depends(get_current_user)
):
    """Initialize Paystack payment for a course"""
    # Get course
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course["is_free"]:
        raise HTTPException(status_code=400, detail="This course is free")
    
    # Check if user already has access
    existing_payment = await db.payments.find_one({
        "user_id": current_user.id,
        "course_id": course_id,
        "status": "completed"
    })
    if existing_payment:
        raise HTTPException(status_code=400, detail="You already have access to this course")
    
    # Convert price to kobo (Paystack uses kobo for NGN)
    amount_in_kobo = int(course["price"] * 100)
    
    # Generate reference
    reference = f"CBT_{course_id}_{current_user.id}_{uuid.uuid4().hex[:8]}"
    
    # Create payment transaction record
    transaction = PaymentTransaction(
        user_id=current_user.id,
        course_id=course_id,
        amount=course["price"],
        paystack_reference=reference,
        status="pending"
    )
    
    await db.payments.insert_one(transaction.dict())
    
    # In production, you would initialize with Paystack here
    # paystack_secret = os.environ.get('PAYSTACK_SECRET_KEY')
    # if not paystack_secret:
    #     raise HTTPException(status_code=500, detail="Payment configuration error")
    
    # Mock Paystack initialization response
    # TODO: Replace with actual Paystack API call
    # url = "https://api.paystack.co/transaction/initialize"
    # headers = {
    #     "Authorization": f"Bearer {paystack_secret}",
    #     "Content-Type": "application/json"
    # }
    # data = {
    #     "email": current_user.email,
    #     "amount": amount_in_kobo,
    #     "currency": "NGN",
    #     "reference": reference,
    #     "callback_url": f"{request.base_url}api/payments/callback"
    # }
    # response = requests.post(url, json=data, headers=headers)
    
    # For now, return mock payment URL structure
    return {
        "status": "success",
        "message": "Payment initialized",
        "data": {
            "authorization_url": f"https://checkout.paystack.com/{reference}",
            "access_code": f"access_code_{reference}",
            "reference": reference
        }
    }

@api_router.post("/payments/verify/{reference}")
async def verify_payment(reference: str):
    """Verify Paystack payment"""
    # Find payment transaction
    payment = await db.payments.find_one({"paystack_reference": reference})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # In production, verify with Paystack
    # paystack_secret = os.environ.get('PAYSTACK_SECRET_KEY')
    # url = f"https://api.paystack.co/transaction/verify/{reference}"
    # headers = {"Authorization": f"Bearer {paystack_secret}"}
    # response = requests.get(url, headers=headers)
    # verification_data = response.json()
    
    # Mock verification for demo (in production, use actual Paystack response)
    verification_success = True  # This would come from Paystack API
    
    if verification_success:
        # Update payment status
        await db.payments.update_one(
            {"paystack_reference": reference},
            {"$set": {"status": "completed"}}
        )
        
        return {
            "status": "success",
            "message": "Payment verified successfully",
            "data": {
                "reference": reference,
                "status": "completed"
            }
        }
    else:
        await db.payments.update_one(
            {"paystack_reference": reference},
            {"$set": {"status": "failed"}}
        )
        
        return {
            "status": "failed",
            "message": "Payment verification failed"
        }

@api_router.post("/payments/webhook")
async def paystack_webhook(request: Request):
    """Handle Paystack webhooks"""
    try:
        # Get raw body
        body = await request.body()
        
        # In production, verify webhook signature
        # paystack_secret = os.environ.get('PAYSTACK_SECRET_KEY')
        # signature = request.headers.get('X-Paystack-Signature')
        # expected_signature = hmac.new(
        #     paystack_secret.encode('utf-8'),
        #     body,
        #     hashlib.sha512
        # ).hexdigest()
        
        # if signature != expected_signature:
        #     raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        event_data = await request.json()
        
        if event_data.get("event") == "charge.success":
            reference = event_data["data"]["reference"]
            
            # Update payment status
            await db.payments.update_one(
                {"paystack_reference": reference},
                {"$set": {"status": "completed"}}
            )
            
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

@api_router.get("/payments/status/{course_id}")
async def get_payment_status(
    course_id: str,
    current_user: User = Depends(get_current_user)
):
    """Check if user has paid for a course"""
    payment = await db.payments.find_one({
        "user_id": current_user.id,
        "course_id": course_id,
        "status": "completed"
    })
    
    return {
        "has_access": payment is not None,
        "payment_status": payment["status"] if payment else "not_paid"
    }

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()