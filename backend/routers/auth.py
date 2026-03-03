"""
Authentication Router - Simple admin password auth with token
"""
import hashlib
import hmac
import time
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from ..config import ADMIN_PASSWORD, ADMIN_SECRET_KEY

router = APIRouter()


def _generate_token() -> str:
    """Génère un token admin signé avec timestamp"""
    timestamp = str(int(time.time()))
    signature = hmac.new(
        ADMIN_SECRET_KEY.encode(),
        timestamp.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{timestamp}.{signature}"


def verify_admin_token(token: str) -> bool:
    """Vérifie qu'un token admin est valide (et pas expiré > 7 jours)"""
    if not token:
        return False
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return False
        timestamp_str, signature = parts
        timestamp = int(timestamp_str)
        
        # Vérifier l'expiration (7 jours)
        if time.time() - timestamp > 7 * 24 * 3600:
            return False
        
        # Vérifier la signature
        expected = hmac.new(
            ADMIN_SECRET_KEY.encode(),
            timestamp_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


def require_admin(authorization: Optional[str] = Header(None)):
    """Dependency FastAPI pour vérifier l'auth admin"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Non autorisé")
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")
    return True


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(request: LoginRequest):
    """Authentification admin avec mot de passe"""
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Auth non configurée")
    
    if request.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    
    token = _generate_token()
    return {"success": True, "token": token}


@router.get("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """Vérifie si un token est valide"""
    if not authorization:
        return {"valid": False}
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    return {"valid": verify_admin_token(token)}
