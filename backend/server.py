from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import base64


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'tfd-secret-key-2025-turkish-armed-forces')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# ============ MODELS ============

class UserRegister(BaseModel):
    username: str
    nickname: str
    email: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    nickname: str
    email: Optional[str] = None
    role: str = "user"  # user, admin, founder
    profile_picture: Optional[str] = None
    online_status: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProfilePictureUpdate(BaseModel):
    profile_picture: str

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    username: str
    nickname: str
    profile_picture: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessageCreate(BaseModel):
    message: str

class Announcement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    admin_id: str
    admin_name: str
    admin_nickname: str
    title: str
    content: str
    image_data: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    image_data: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Convert timestamp if needed
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return User(**user)


# ============ AUTH ROUTES ============

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    # Check if username already exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash password
    hashed_pw = hash_password(user_data.password)
    
    # Create user
    user = User(
        username=user_data.username,
        nickname=user_data.nickname,
        email=user_data.email,
        role="user",
        profile_picture=f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_data.username}",
        online_status=True
    )
    
    # Save to database
    user_dict = user.model_dump()
    user_dict['password'] = hashed_pw
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/login", response_model=Token)
async def login(login_data: UserLogin):
    # Find user
    user_doc = await db.users.find_one({"username": login_data.username})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Verify password
    if not verify_password(login_data.password, user_doc['password']):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Update online status
    await db.users.update_one({"id": user_doc['id']}, {"$set": {"online_status": True}})
    
    # Convert timestamp
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/admin-login", response_model=Token)
async def admin_login(login_data: AdminLogin):
    # Hardcoded admin credentials
    admin_credentials = {
        "Admintfd": {"password": "tfdadamdır", "role": "admin", "nickname": "TFD Admin"},
        "Efe": {"password": "Efeisholderr", "role": "founder", "nickname": "Founder Efe"}
    }
    
    if login_data.username not in admin_credentials:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    admin_info = admin_credentials[login_data.username]
    if login_data.password != admin_info["password"]:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    # Check if admin user exists in database, if not create
    user_doc = await db.users.find_one({"username": login_data.username})
    
    if not user_doc:
        # Create admin user
        user = User(
            username=login_data.username,
            nickname=admin_info["nickname"],
            email=None,
            role=admin_info["role"],
            profile_picture=f"https://api.dicebear.com/7.x/bottts/svg?seed={login_data.username}",
            online_status=True
        )
        
        user_dict = user.model_dump()
        user_dict['password'] = hash_password(login_data.password)
        user_dict['created_at'] = user_dict['created_at'].isoformat()
        
        await db.users.insert_one(user_dict)
    else:
        # Update online status and role
        await db.users.update_one(
            {"id": user_doc['id']}, 
            {"$set": {"online_status": True, "role": admin_info["role"]}}
        )
        
        if isinstance(user_doc.get('created_at'), str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
        
        user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # Update online status
    await db.users.update_one({"id": current_user.id}, {"$set": {"online_status": False}})
    return {"message": "Logged out successfully"}


# ============ USER ROUTES ============

@api_router.get("/users/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.get("/users/online-count")
async def get_online_count():
    count = await db.users.count_documents({"online_status": True})
    return {"online_count": count}

@api_router.put("/users/profile-picture", response_model=User)
async def update_profile_picture(data: ProfilePictureUpdate, current_user: User = Depends(get_current_user)):
    # Update profile picture in database
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"profile_picture": data.profile_picture}}
    )
    
    # Get updated user
    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return User(**{k: v for k, v in user_doc.items() if k != 'password'})


# ============ CHAT ROUTES ============

@api_router.get("/chat/messages", response_model=List[ChatMessage])
async def get_messages(current_user: User = Depends(get_current_user)):
    messages = await db.chat_messages.find({}, {"_id": 0}).sort("timestamp", 1).to_list(500)
    
    # Convert timestamps
    for msg in messages:
        if isinstance(msg['timestamp'], str):
            msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
    
    return messages

@api_router.post("/chat/messages", response_model=ChatMessage)
async def send_message(message_data: ChatMessageCreate, current_user: User = Depends(get_current_user)):
    message = ChatMessage(
        user_id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        profile_picture=current_user.profile_picture,
        message=message_data.message
    )
    
    msg_dict = message.model_dump()
    msg_dict['timestamp'] = msg_dict['timestamp'].isoformat()
    
    await db.chat_messages.insert_one(msg_dict)
    
    return message


# ============ ANNOUNCEMENT ROUTES ============

@api_router.get("/announcements", response_model=List[Announcement])
async def get_announcements(current_user: User = Depends(get_current_user)):
    announcements = await db.announcements.find({}, {"_id": 0}).sort("timestamp", -1).to_list(100)
    
    # Convert timestamps
    for ann in announcements:
        if isinstance(ann['timestamp'], str):
            ann['timestamp'] = datetime.fromisoformat(ann['timestamp'])
    
    return announcements

@api_router.post("/announcements", response_model=Announcement)
async def create_announcement(announcement_data: AnnouncementCreate, current_user: User = Depends(get_current_user)):
    # Check if user is admin or founder
    if current_user.role not in ["admin", "founder"]:
        raise HTTPException(status_code=403, detail="Only admins and founders can create announcements")
    
    announcement = Announcement(
        admin_id=current_user.id,
        admin_name=current_user.username,
        admin_nickname=current_user.nickname,
        title=announcement_data.title,
        content=announcement_data.content,
        image_data=announcement_data.image_data
    )
    
    ann_dict = announcement.model_dump()
    ann_dict['timestamp'] = ann_dict['timestamp'].isoformat()
    
    await db.announcements.insert_one(ann_dict)
    
    return announcement


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
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
