"""
GitLab OAuth Authentication
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
import httpx
import os

from ..db.database import get_db
from ..models.models import User
from .jwt import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user, UserResponse

router = APIRouter()

# GitLab OAuth Configuration
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID", "")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET", "")
GITLAB_REDIRECT_URI = os.getenv("GITLAB_REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

GITLAB_AUTHORIZE_URL = "https://gitlab.com/oauth/authorize"
GITLAB_TOKEN_URL = "https://gitlab.com/oauth/token"
GITLAB_USER_URL = "https://gitlab.com/api/v4/user"


@router.get("/login")
async def login():
    """Redirect to GitLab OAuth"""
    if not GITLAB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GitLab OAuth not configured")
    
    params = {
        "client_id": GITLAB_CLIENT_ID,
        "redirect_uri": GITLAB_REDIRECT_URI,
        "response_type": "code",
        "scope": "read_user openid email",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GITLAB_AUTHORIZE_URL}?{query}")


@router.get("/callback")
async def callback(code: str, db: Session = Depends(get_db)):
    """Handle GitLab OAuth callback"""
    if not GITLAB_CLIENT_ID or not GITLAB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitLab OAuth not configured")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITLAB_TOKEN_URL,
            data={
                "client_id": GITLAB_CLIENT_ID,
                "client_secret": GITLAB_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GITLAB_REDIRECT_URI,
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        token_data = token_response.json()
        gitlab_access_token = token_data.get("access_token")
        
        # Get user info from GitLab
        user_response = await client.get(
            GITLAB_USER_URL,
            headers={"Authorization": f"Bearer {gitlab_access_token}"}
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        gitlab_user = user_response.json()
    
    # Create or update user in database
    user = db.query(User).filter(User.gitlab_id == str(gitlab_user["id"])).first()
    
    if not user:
        # Check if user with this email exists
        user = db.query(User).filter(User.email == gitlab_user["email"]).first()
        if user:
            # Link existing user to GitLab
            user.gitlab_id = str(gitlab_user["id"])
        else:
            # Create new user
            # First user becomes admin
            is_first_user = db.query(User).count() == 0
            user = User(
                email=gitlab_user["email"],
                name=gitlab_user.get("name") or gitlab_user.get("username"),
                gitlab_id=str(gitlab_user["id"]),
                avatar_url=gitlab_user.get("avatar_url"),
                role="admin" if is_first_user else "user",
            )
            db.add(user)
    else:
        # Update existing user
        user.name = gitlab_user.get("name") or gitlab_user.get("username")
        user.avatar_url = gitlab_user.get("avatar_url")
    
    db.commit()
    db.refresh(user)
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": user.email, "gitlab_id": user.gitlab_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Redirect to frontend with token
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={access_token}")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@router.post("/logout")
async def logout():
    """Logout - frontend should clear token"""
    return {"message": "Logged out successfully"}
