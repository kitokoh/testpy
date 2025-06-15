from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext # For password hashing if we were creating them here, not needed for verify_user_password
from datetime import datetime, timedelta, timezone # Ensure timezone is imported
from typing import Optional
import os # Added import

import db as db_manager # To access user verification
from .models import TokenData, UserInDB # Import UserInDB from local models

# Configuration (replace with your actual secret key and algorithm)
SECRET_KEY = os.getenv("API_SECRET_KEY") # IMPORTANT: Change this in a real app!
if not SECRET_KEY:
    raise RuntimeError("API_SECRET_KEY environment variable not set. Application cannot start securely.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# We don't need pwd_context if db_manager.verify_user_password already handles hashing comparison
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password_from_db: str) -> bool:
    # This function should ideally call db_manager.verify_user_password's logic
    # or db_manager.verify_user_password should be adapted if it needs raw plain pass.
    # For now, let's assume db_manager.verify_user_password takes username and plain_password
    # and returns user details if valid, or None otherwise.
    # This function itself is not directly used if authenticate_user does the job.
    # return pwd_context.verify(plain_password, hashed_password_from_db)
    # This is a placeholder, actual verification happens in authenticate_user via db_manager.
    return True # Placeholder, logic is in authenticate_user

def get_user(username: str) -> Optional[UserInDB]:
    db_user = db_manager.get_user_by_username(username)
    if db_user:
        # Adapt db_user dict to UserInDB model
        return UserInDB(
            username=db_user.get('username'),
            email=db_user.get('email'),
            full_name=db_user.get('full_name'),
            role=db_user.get('role'),
            is_active=db_user.get('is_active', False), # Default to False if not present
            user_id=db_user.get('user_id')
        )
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# --- Router for token endpoint ---
from fastapi import APIRouter
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Logs in a user and returns an access token.

    Processes OAuth2 password flow request form to authenticate the user.
    On successful authentication, an access token is generated and returned.
    """
    # db_manager.verify_user_password expects username and plain password,
    # and returns user dict if valid, None otherwise.
    user = db_manager.verify_user_password(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.get('username')}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
