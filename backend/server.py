from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
paystack_secret = os.environ.get("PAYSTACK_SECRET_KEY")
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
import hashlib
import requests
import hmac
from typing import Optional
from pydantic import BaseModel, EmailStr

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-ex8x.onrender.com",
        "https://app-noozue1hv-idowugudness01-8172s-projects.vercel.app",
        "https://app-swart-three.vercel.app",
        "http://localhost:3000",  # Local development
        "https://cbt.atcsedu.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to the API"}

@app.get("/test")
def test_cors():
    return {"status": "CORS working"}

class LoginPayload(BaseModel):
    email: EmailStr
    password: str

# Define routes using `api_router`
@api_router.post("/auth/login")
async def login(payload: LoginPayload):
    return {"message": "Login working"}

# Define Pydantic model for /auth/register
class RegisterPayload(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str

# Use it in the route
@api_router.post("/auth/register")
async def register(payload: RegisterPayload):
    return {"message": "Register working"}

# Then include the router
app.include_router(api_router, prefix="/api")

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

# Enhanced PDF Parser Function
def parse_pdf_to_questions(pdf_content: bytes) -> List[Question]:
    """Parse PDF content and extract questions using multiple enhanced methods"""
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
        
        print(f"PDF Analysis: Total pages: {len(pdf.pages)}, Total text length: {len(text)}")
        
        # Try multiple parsing methods and combine results
        all_questions = []
        
        # Method 1: Enhanced structured format parsing
        questions_method1 = parse_enhanced_structured_format(text)
        if questions_method1:
            all_questions.extend(questions_method1)
            print(f"Method 1 (Enhanced Structured): Found {len(questions_method1)} questions")
        
        # Method 2: Multi-line question parsing
        questions_method2 = parse_multiline_questions(text)
        if questions_method2:
            all_questions.extend(questions_method2)
            print(f"Method 2 (Multi-line): Found {len(questions_method2)} questions")
        
        # Method 3: Continuous text parsing
        questions_method3 = parse_continuous_text(text)
        if questions_method3:
            all_questions.extend(questions_method3)
            print(f"Method 3 (Continuous): Found {len(questions_method3)} questions")
        
        # Method 4: Page-by-page parsing
        questions_method4 = parse_page_by_page(pdf)
        if questions_method4:
            all_questions.extend(questions_method4)
            print(f"Method 4 (Page-by-page): Found {len(questions_method4)} questions")
        
        # Remove duplicates based on question text similarity
        unique_questions = remove_duplicate_questions(all_questions)
        print(f"Total unique questions after deduplication: {len(unique_questions)}")
        
        return unique_questions
        
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return []

def remove_duplicate_questions(questions: List[Question]) -> List[Question]:
    """Remove duplicate questions based on text similarity"""
    unique_questions = []
    seen_questions = set()
    
    for question in questions:
        # Create a normalized version for comparison
        normalized = question.question_text.lower().strip()[:100]  # First 100 chars
        
        if normalized not in seen_questions:
            seen_questions.add(normalized)
            unique_questions.append(question)
    
    return unique_questions

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

def parse_enhanced_structured_format(text: str) -> List[Question]:
    """Enhanced structured format parsing with better pattern recognition"""
    questions = []
    
    # Try multiple patterns for structured format
    patterns = [
        r'\n\d+\nQuestion\n',  # Original pattern
        r'\n\d+\.\s*Question\s*\n',  # Numbered with dots
        r'\nQuestion\s*\d+\s*\n',  # Question with number
        r'\n\d+\)\s*',  # Numbered with parentheses
        r'\n\d+\s+[A-Z]',  # Numbered followed by text
    ]
    
    for pattern in patterns:
        question_blocks = re.split(pattern, text, flags=re.IGNORECASE)
        if len(question_blocks) > 3:  # Need at least 3 blocks for meaningful extraction
            for block in question_blocks[1:]:
                question = extract_question_from_block(block)
                if question:
                    questions.append(question)
            break
    
    # If no questions found with above patterns, try GST104 specific format
    if not questions:
        questions = parse_gst104_format(text)
    
    return questions

def parse_gst104_format(text: str) -> List[Question]:
    """Parse GST104 specific format"""
    questions = []
    
    # Split by question numbers followed by "Question"
    question_blocks = re.split(r'\n(\d+)\nQuestion\n', text)
    
    for i in range(1, len(question_blocks), 2):
        if i + 1 < len(question_blocks):
            question_num = question_blocks[i]
            question_content = question_blocks[i + 1]
            
            try:
                lines = [line.strip() for line in question_content.split('\n') if line.strip()]
                
                # Find question text (after "Mark" line, before "Select one:")
                question_text = ''
                options = []
                collecting_question = False
                collecting_options = False
                
                for line in lines:
                    if 'Mark' in line and 'out of' in line:
                        collecting_question = True
                        continue
                    
                    if line == 'Select one:':
                        collecting_question = False
                        collecting_options = True
                        continue
                    
                    if collecting_question and line and not line.startswith('http://'):
                        question_text += line + ' '
                    
                    if collecting_options and line and not line.startswith('http://') and not line.startswith('4/'):
                        # Stop collecting if we hit the next question or page info
                        if re.match(r'^\d+$', line) or 'Question' in line:
                            break
                        if len(options) < 4:
                            options.append(line)
                
                question_text = question_text.strip()
                
                if question_text and len(options) >= 2:
                    questions.append(Question(
                        question_text=question_text,
                        options=options[:4],
                        correct_answer=0  # Default to first option
                    ))
                    
            except Exception as e:
                continue
    
    return questions

def parse_multiline_questions(text: str) -> List[Question]:
    """Parse questions that span multiple lines with enhanced detection"""
    questions = []
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Enhanced question indicators
        question_patterns = [
            r'^\d+[\.\)\s]+',  # 1. 2) 3 
            r'^Q\d*[\.\:\s]*',  # Q1. Q: 
            r'^\d+\s*[A-Z]',   # 1 The question...
            r'question\s*\d*',  # Question 1
        ]
        
        is_question = any(re.match(pattern, line, re.IGNORECASE) for pattern in question_patterns)
        
        if is_question or 'question' in line.lower():
            # Clean up question text
            question_text = line
            for pattern in question_patterns:
                question_text = re.sub(pattern, '', question_text, flags=re.IGNORECASE)
            question_text = re.sub(r'question\s*\d*[\.\:]?\s*', '', question_text, flags=re.IGNORECASE)
            
            i += 1
            # Continue collecting question text
            while i < len(lines) and not re.match(r'^[A-Da-d][\.\)]\s*', lines[i].strip()):
                next_line = lines[i].strip()
                if (next_line and 
                    not next_line.lower().startswith('select') and
                    not re.match(r'^\d+[\.\)\s]+', next_line) and
                    'http://' not in next_line):
                    question_text += ' ' + next_line
                i += 1
            
            # Collect options (both uppercase and lowercase)
            options = []
            while i < len(lines) and re.match(r'^[A-Da-d][\.\)]\s*', lines[i].strip()):
                option_text = re.sub(r'^[A-Da-d][\.\)]\s*', '', lines[i].strip())
                if option_text and len(option_text) > 2:  # Minimum length check
                    options.append(option_text)
                i += 1
            
            question_text = question_text.strip()
            if question_text and len(question_text) > 10 and len(options) >= 2:
                questions.append(Question(
                    question_text=question_text,
                    options=options[:4],
                    correct_answer=0
                ))
        else:
            i += 1
    
    return questions

def parse_continuous_text(text: str) -> List[Question]:
    """Parse questions from continuous text with improved patterns"""
    questions = []
    
    # Multiple patterns for different question formats
    patterns = [
        # Pattern 1: Question ending with ? followed by options
        r'([^.!?\n]{20,}?\?[^A-D\n]*?)([A-D][\.\)][^A-D]*[A-D][\.\)][^A-D]*(?:[A-D][\.\)][^A-D]*)?(?:[A-D][\.\)][^A-D]*)?)',
        # Pattern 2: Statement followed by options
        r'(\d+[\.\)]\s*[^A-D]{30,}?)([A-D][\.\)][^A-D]*[A-D][\.\)][^A-D]*(?:[A-D][\.\)][^A-D]*)?(?:[A-D][\.\)][^A-D]*)?)',
        # Pattern 3: "Which of the following" type questions
        r'([Ww]hich\s+of\s+the\s+following[^A-D]{10,}?)([A-D][\.\)][^A-D]*[A-D][\.\)][^A-D]*(?:[A-D][\.\)][^A-D]*)?(?:[A-D][\.\)][^A-D]*)?)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            question_text = match.group(1).strip()
            options_text = match.group(2).strip()
            
            # Clean question text
            question_text = re.sub(r'^\d+[\.\)]\s*', '', question_text)
            question_text = ' '.join(question_text.split())  # Normalize whitespace
            
            # Extract options
            option_matches = re.findall(r'([A-D])[\.\)]([^A-D]*?)(?=[A-D][\.\)]|$)', options_text)
            options = [opt[1].strip() for opt in option_matches if opt[1].strip() and len(opt[1].strip()) > 3]
            
            if question_text and len(question_text) > 15 and len(options) >= 2:
                questions.append(Question(
                    question_text=question_text,
                    options=options[:4],
                    correct_answer=0
                ))
    
    return questions

def parse_page_by_page(pdf) -> List[Question]:
    """Parse questions page by page with comprehensive methods"""
    questions = []
    
    for page_num, page in enumerate(pdf.pages):
        page_text = page.extract_text()
        if not page_text:
            continue
        
        # Clean page text
        page_text = re.sub(r'http://[^\s]*', '', page_text)  # Remove URLs
        page_text = re.sub(r'\d+/\d+/\d+', '', page_text)   # Remove dates
        
        page_questions = []
        
        # Method 1: Numbered questions
        numbered_pattern = r'\n(\d+)[\.\)]\s*([^0-9\n][^\n]*)'
        numbered_matches = re.findall(numbered_pattern, page_text)
        
        for match in numbered_matches:
            question_num = match[0]
            question_start = match[1]
            
            # Find the full question and options
            question_block = extract_full_question_block(page_text, question_num, question_start)
            if question_block:
                parsed_question = parse_question_block(question_block)
                if parsed_question:
                    page_questions.append(parsed_question)
        
        # Method 2: Look for Q: patterns
        q_pattern = r'Q\d*[\.\:]?\s*([^A-D\n]{20,}?)([A-D][\.\)][^A-D]*)'
        q_matches = re.finditer(q_pattern, page_text, re.IGNORECASE | re.DOTALL)
        
        for match in q_matches:
            question_text = match.group(1).strip()
            options_start = match.group(2)
            
            # Extract full options
            options = extract_options_from_position(page_text, match.end() - len(options_start))
            
            if question_text and len(question_text) > 10 and len(options) >= 2:
                page_questions.append(Question(
                    question_text=question_text,
                    options=options,
                    correct_answer=0
                ))
        
        questions.extend(page_questions)
    
    return questions

def extract_full_question_block(text: str, question_num: str, question_start: str) -> str:
    """Extract the full question block including all options"""
    # Find where this question starts
    start_pattern = f"{question_num}[\\.)\\s]+{re.escape(question_start[:20])}"
    start_match = re.search(start_pattern, text)
    
    if not start_match:
        return ""
    
    start_pos = start_match.start()
    
    # Find where the next question starts
    next_q_pattern = f"\\n{int(question_num) + 1}[\\.)\\s]+"
    next_match = re.search(next_q_pattern, text[start_pos + 10:])
    
    if next_match:
        end_pos = start_pos + 10 + next_match.start()
        return text[start_pos:end_pos]
    else:
        # If no next question, take a reasonable chunk
        return text[start_pos:start_pos + 500]

def parse_question_block(block: str) -> Optional[Question]:
    """Parse a complete question block"""
    lines = [line.strip() for line in block.split('\n') if line.strip()]
    
    if not lines:
        return None
    
    # Extract question text (everything before first option)
    question_lines = []
    options = []
    
    for line in lines:
        if re.match(r'^[A-Da-d][\.\)]\s*', line):
            # This is an option
            option_text = re.sub(r'^[A-Da-d][\.\)]\s*', '', line)
            if option_text and len(option_text) > 2:
                options.append(option_text)
        elif not options:  # Still collecting question text
            # Clean the line
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
            if cleaned and 'Mark' not in cleaned and 'http://' not in cleaned:
                question_lines.append(cleaned)
    
    question_text = ' '.join(question_lines).strip()
    
    if question_text and len(question_text) > 10 and len(options) >= 2:
        return Question(
            question_text=question_text,
            options=options[:4],
            correct_answer=0
        )
    
    return None

def extract_options_from_position(text: str, start_pos: int) -> List[str]:
    """Extract options starting from a specific position"""
    options = []
    remaining_text = text[start_pos:]
    
    # Look for A. B. C. D. patterns
    option_pattern = r'([A-D])[\.\)]([^A-D]*?)(?=[A-D][\.\)]|$)'
    matches = re.findall(option_pattern, remaining_text[:500])  # Limit search range
    
    for match in matches:
        option_text = match[1].strip()
        if option_text and len(option_text) > 2:
            options.append(option_text)
    
    return options[:4]

def extract_question_from_block(block: str) -> Optional[Question]:
    """Extract a single question from a text block"""
    lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
    
    if not lines:
        return None
    
    question_text = ''
    options = []
    collecting_question = True
    
    for line in lines:
        # Skip metadata lines
        if any(skip in line.lower() for skip in ['mark', 'out of', 'http://', 'page', 'time']):
            continue
        
        # Check for option markers
        if re.match(r'^[A-D][\.\)]\s*', line):
            collecting_question = False
            option_text = re.sub(r'^[A-D][\.\)]\s*', '', line)
            if option_text:
                options.append(option_text)
        elif collecting_question and line and line != 'Select one:':
            question_text += line + ' '
    
    question_text = question_text.strip()
    
    if question_text and len(options) >= 2:
        return Question(
            question_text=question_text,
            options=options[:4],
            correct_answer=0
        )
    
    return None

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

@api_router.delete("/admin/courses/{course_id}")
async def delete_course(
    course_id: str,
    current_user: User = Depends(get_admin_user)
):
    """Delete a course and all associated data"""
    # Check if course exists
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    try:
        # Delete associated test attempts
        attempts_deleted = await db.test_attempts.delete_many({"course_id": course_id})
        
        # Delete associated payment transactions
        payments_deleted = await db.payments.delete_many({"course_id": course_id})
        
        # Delete the course itself
        result = await db.courses.delete_one({"id": course_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Course not found")
        
        return {
            "message": "Course deleted successfully",
            "course_title": course["title"],
            "attempts_deleted": attempts_deleted.deleted_count,
            "payments_deleted": payments_deleted.deleted_count
        }
        
    except Exception as e:
        print(f"Error deleting course: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete course")

@api_router.get("/admin/courses/{course_id}/details")
async def get_course_admin_details(
    course_id: str,
    current_user: User = Depends(get_admin_user)
):
    """Get detailed course information for admin"""
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get statistics
    attempts_count = await db.test_attempts.count_documents({"course_id": course_id})
    payments_count = await db.payments.count_documents({"course_id": course_id, "status": "completed"})
    
    return {
        "course": Course(**course),
        "statistics": {
            "total_attempts": attempts_count,
            "total_payments": payments_count,
            "questions_count": len(course["questions"]),
            "created_at": course["created_at"]
        }
    }

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
import requests  # Add at the top if not present


@api_router.post("/payments/initialize")
async def initialize_payment(
    course_id: str,
    current_user: User = Depends(get_current_user)
):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers, timeout=10)
        resp_data = response.json()

    """Initialize Paystack payment for a course"""
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course["is_free"]:
        raise HTTPException(status_code=400, detail="This course is free")
    existing_payment = await db.payments.find_one({
        "user_id": current_user.id,
        "course_id": course_id,
        "status": "completed"
    })
    if existing_payment:
        raise HTTPException(status_code=400, detail="You already have access to this course")
    amount_in_kobo = int(course["price"] * 100)
    reference = f"CBT_{course_id}_{current_user.id}_{uuid.uuid4().hex[:8]}"
    transaction = PaymentTransaction(
        user_id=current_user.id,
        course_id=course_id,
        amount=course["price"],
        paystack_reference=reference,
        status="pending"
    )
    await db.payments.insert_one(transaction.dict())
    paystack_secret = os.environ.get('PAYSTACK_SECRET_KEY')
    if not paystack_secret:
        raise HTTPException(status_code=500, detail="Payment configuration error")
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {paystack_secret}",
        "Content-Type": "application/json"
    }
    data = {
        "email": current_user.email,
        "amount": amount_in_kobo,
        "currency": "NGN",
        "reference": reference,
        # You can set your real callback URL here
        # "callback_url": "https://your-frontend-url.com/payment/callback"
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        resp_data = response.json()
        if not resp_data.get("status"):
            raise HTTPException(status_code=500, detail=resp_data.get("message", "Paystack error"))
        return resp_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Paystack error: {str(e)}")

@api_router.post("/payments/verify/{reference}")
async def verify_payment(reference: str):
    """Verify Paystack payment"""
    payment = await db.payments.find_one({"paystack_reference": reference})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    paystack_secret = os.environ.get('PAYSTACK_SECRET_KEY')
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {paystack_secret}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        verification_data = response.json()
        if verification_data.get("status") and verification_data.get("data", {}).get("status") == "success":
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
                "message": verification_data.get("message", "Payment verification failed")
            }
    except Exception as e:
        await db.payments.update_one(
            {"paystack_reference": reference},
            {"$set": {"status": "failed"}}
        )
        raise HTTPException(status_code=500, detail=f"Paystack verification error: {str(e)}")

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
