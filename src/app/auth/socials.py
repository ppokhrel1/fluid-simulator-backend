# app/auth/social.py
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
import secrets
from urllib.parse import urlencode
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.core.config import settings
from src.app.core.db.database import async_get_db
from src.app.models.user import User, OAuthAccount
from .manager import get_user_manager

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple OAuth redirect endpoints
@router.get("/{provider}")
async def login_with_provider(provider: str):
    """Start OAuth flow by redirecting to provider's authorization page"""
    if provider == "google":
        # Redirect to Google OAuth authorization endpoint
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/google/callback",
            "access_type": "offline",
            "prompt": "select_account"
        }
        redirect_uri = f"{base_url}?{urlencode(params)}"
        
    elif provider == "facebook":
        base_url = "https://www.facebook.com/v12.0/dialog/oauth"
        params = {
            "client_id": settings.FACEBOOK_CLIENT_ID,
            "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/facebook/callback",
            "scope": "email,public_profile",
            "response_type": "code"
        }
        redirect_uri = f"{base_url}?{urlencode(params)}"
        
    elif provider == "linkedin":
        base_url = "https://www.linkedin.com/oauth/v2/authorization"
        params = {
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/linkedin/callback", 
            "scope": "openid profile email",
            "response_type": "code"
        }
        redirect_uri = f"{base_url}?{urlencode(params)}"
        
    else:
        raise HTTPException(status_code=404, detail="Provider not supported")
    
    return RedirectResponse(redirect_uri)

async def exchange_code_for_token(provider: str, code: str, redirect_uri: str):
    """Exchange OAuth code for access token"""
    token_urls = {
        "google": "https://oauth2.googleapis.com/token",
        "facebook": "https://graph.facebook.com/v12.0/oauth/access_token",
        "linkedin": "https://www.linkedin.com/oauth/v2/accessToken"
    }
    
    client_ids = {
        "google": settings.GOOGLE_CLIENT_ID,
        "facebook": settings.FACEBOOK_CLIENT_ID, 
        "linkedin": settings.LINKEDIN_CLIENT_ID
    }
    
    client_secrets = {
        "google": settings.GOOGLE_CLIENT_SECRET,
        "facebook": settings.FACEBOOK_CLIENT_SECRET,
        "linkedin": settings.LINKEDIN_CLIENT_SECRET
    }
    
    data = {
        "client_id": client_ids[provider],
        "client_secret": client_secrets[provider],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_urls[provider], data=data)
        return response.json()

async def get_user_info(provider: str, access_token: str):
    """Get user info from OAuth provider"""
    user_info_urls = {
        "google": "https://www.googleapis.com/oauth2/v3/userinfo",
        "facebook": "https://graph.facebook.com/v12.0/me?fields=id,name,email,picture",
        "linkedin": "https://api.linkedin.com/v2/me?projection=(id,firstName,lastName,profilePicture(displayImage~:playableStreams))"
    }
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(user_info_urls[provider], headers=headers)
        user_info = response.json()
        
        # Get email for LinkedIn (requires separate API call)
        if provider == "linkedin":
            email_response = await client.get(
                "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                headers=headers
            )
            email_data = email_response.json()
            if email_data.get('elements'):
                user_info['email'] = email_data['elements'][0]['handle~']['emailAddress']
        
        return user_info

async def get_or_create_user_from_oauth(db: AsyncSession, provider: str, user_info: dict, access_token: str):
    """Get existing user or create new user from OAuth data"""
    user_manager = await get_user_manager()
    
    # Extract user data based on provider
    if provider == "google":
        email = user_info.get("email")
        name = user_info.get("name")
        oauth_id = user_info.get("sub")
    elif provider == "facebook":
        email = user_info.get("email")
        name = user_info.get("name") 
        oauth_id = user_info.get("id")
    elif provider == "linkedin":
        email = user_info.get("email")
        first_name = user_info['firstName']['localized'].get('en_US', '')
        last_name = user_info['lastName']['localized'].get('en_US', '')
        name = f"{first_name} {last_name}".strip()
        oauth_id = user_info.get("id")
    
    # Check if OAuth account already exists
    stmt = select(OAuthAccount).where(
        OAuthAccount.oauth_name == provider,
        OAuthAccount.account_id == oauth_id
    )
    result = await db.execute(stmt)
    existing_oauth = result.scalar_one_or_none()
    
    if existing_oauth:
        # Existing OAuth account - return the user
        stmt = select(User).where(User.id == existing_oauth.user_id)
        result = await db.execute(stmt)
        return result.scalar_one()
    
    # Check if user with email already exists
    if email:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # User exists but hasn't connected this OAuth provider yet
            user = existing_user
        else:
            # Create new user
            user_data = {
                "email": email,
                "password": None,  # OAuth users don't need passwords
                "is_active": True,
                "is_verified": True,  # OAuth providers verify emails
                "first_name": name.split(' ')[0] if name else "",
                "last_name": ' '.join(name.split(' ')[1:]) if name else ""
            }
            user = await user_manager.create(user_data, safe=True)
    else:
        # No email - create user with placeholder
        user_data = {
            "email": f"{provider}_{oauth_id}@placeholder.com",
            "password": None,
            "is_active": True,
            "is_verified": False,
            "first_name": name.split(' ')[0] if name else "",
            "last_name": ' '.join(name.split(' ')[1:]) if name else ""
        }
        user = await user_manager.create(user_data, safe=True)
    
    # Create OAuth account record
    oauth_account = OAuthAccount(
        oauth_name=provider,
        account_id=oauth_id,
        account_email=email,
        access_token=access_token,
        user_id=user.id
    )
    db.add(oauth_account)
    await db.commit()
    
    return user

@router.get("/{provider}/callback")
async def oauth_callback(
    request: Request,
    provider: str,
    code: str = None,
    error: str = None,
    error_description: str = None,
    db: AsyncSession = Depends(async_get_db)
):
    """Complete OAuth callback that exchanges code for token and creates/authenticates user"""
    print(f"OAuth callback for {provider}: code={code}, error={error}")
    
    if error:
        error_msg = error_description or error
        frontend_url = f"{settings.FRONTEND_URL}/login?error={error_msg}"
        return RedirectResponse(frontend_url)
    
    if not code:
        print(f"No code received from {provider}. Query params: {dict(request.query_params)}")
        frontend_url = f"{settings.FRONTEND_URL}/login?error=no_auth_code_received&provider={provider}"
        return RedirectResponse(frontend_url)
    
    try:
        # Exchange code for access token
        redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/{provider}/callback"
        token_data = await exchange_code_for_token(provider, code, redirect_uri)
        
        if "error" in token_data:
            print(f"Token exchange error: {token_data}")
            frontend_url = f"{settings.FRONTEND_URL}/login?error=token_exchange_failed"
            return RedirectResponse(frontend_url)
        
        access_token = token_data["access_token"]
        
        # Get user info from provider
        user_info = await get_user_info(provider, access_token)
        
        # Get or create user in our database
        user = await get_or_create_user_from_oauth(db, provider, user_info, access_token)
        
        # Generate JWT token for the user (you'll need to implement this based on your auth system)
        # For now, redirect with user ID - you'll need to implement proper JWT generation
        frontend_url = f"{settings.FRONTEND_URL}/oauth-callback?provider={provider}&user_id={user.id}&success=true"
        
        return RedirectResponse(frontend_url)
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        frontend_url = f"{settings.FRONTEND_URL}/login?error=oauth_failed"
        return RedirectResponse(frontend_url)

# Test endpoint to verify configuration
@router.get("/{provider}/test")
async def test_provider_config(provider: str):
    """Test endpoint to check OAuth configuration"""
    config = {
        "google": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/google/callback",
            "configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
        },
        "facebook": {
            "client_id": settings.FACEBOOK_CLIENT_ID,
            "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/facebook/callback", 
            "configured": bool(settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET)
        },
        "linkedin": {
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "redirect_uri": f"{settings.BACKEND_URL}/api/v1/auth/linkedin/callback",
            "configured": bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET)
        }
    }
    
    if provider not in config:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return config[provider]

# Simple health check for OAuth
@router.get("/health")
async def oauth_health():
    """Health check for OAuth endpoints"""
    return {"status": "ok", "message": "OAuth endpoints are working"}