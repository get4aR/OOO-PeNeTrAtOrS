from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import User, get_db
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError # python-jose
from passlib.context import CryptContext


SECRET_KEY = "secretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Hashing algorithm for passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # bcrypt==4.0.1


# Function to hash passwords
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Function to verify a hashed password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# Function to create a JWT access token
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


# Function to verify and decode JWT token
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("Authorization")
    
    if not token:
        print("1")
        return RedirectResponse(url="/login/", status_code=302)
    
    try:
        token = token.split(" ")[1]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            response = RedirectResponse(url="/login/", status_code=302)
            response.delete_cookie("Authorization")
            print("2")
            return response

    except ExpiredSignatureError:
        response = RedirectResponse(url="/login/", status_code=302)
        response.delete_cookie("Authorization")
        print("3")
        return response
            
    except JWTError:
        response = RedirectResponse(url="/login/", status_code=302)
        response.delete_cookie("Authorization")
        print("4")
        return response
    
    user = db.query(User).filter(User.email == email).first()
    
    if user is None:
        response = RedirectResponse(url="/login/", status_code=302)
        response.delete_cookie("Authorization")
        print("5")
        return response
    
    return user
