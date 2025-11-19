import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError

from database import db, create_document, get_documents
from schemas import Shoe, Order

app = FastAPI(title="Formal Shoes Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Security & Auth Setup ===
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-please-change")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
http_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr


# Helpers
class ObjectIdStr(BaseModel):
    id: str


def to_public(doc: dict):
    if not doc:
        return doc
    d = doc.copy()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


@app.get("/")
def read_root():
    return {"message": "Formal Shoes API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# === Auth Endpoints ===
@app.post("/auth/register", response_model=UserPublic)
def register_user(payload: RegisterRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = db["user"].find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "name": payload.name,
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
    }
    user_id = create_document("user", user_doc)
    return UserPublic(id=user_id, name=payload.name, email=payload.email)


@app.post("/auth/login", response_model=Token)
def login_user(payload: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    user = db["user"].find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.get("_id")), "email": user.get("email")})
    return Token(access_token=token)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = db["user"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# === Seed some default shoes if collection empty ===
@app.post("/seed")
def seed_shoes():
    count = db["shoe"].count_documents({}) if db else 0
    if count > 0:
        return {"seeded": False, "message": "Shoes already exist"}

    sample = [
        Shoe(
            title="Oxford Classic",
            description="Handcrafted leather oxford with cap toe",
            brand="Eleganza",
            price=149.99,
            images=[
                "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1600&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1544441893-675973e31985?q=80&w=1600&auto=format&fit=crop",
            ],
            rating=4.7,
            colors=["Black", "Brown"],
        ).model_dump(),
        Shoe(
            title="Derby Modern",
            description="Sleek derby with cushioned insole for all‑day comfort",
            brand="UrbanGent",
            price=129.00,
            images=[
                "https://images.unsplash.com/photo-1528701800489-20be3c2ea4e1?q=80&w=1600&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1519741497674-611481863552?q=80&w=1600&auto=format&fit=crop",
            ],
            rating=4.6,
            colors=["Tan", "Black"],
        ).model_dump(),
        Shoe(
            title="Monk Strap Elite",
            description="Double monk strap in premium full‑grain leather",
            brand="Monarch",
            price=179.50,
            images=[
                "https://images.unsplash.com/photo-1605733512920-0f3c45a3d3b8?q=80&w=1600&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1535046128895-5d09e52971d8?q=80&w=1600&auto=format&fit=crop",
            ],
            rating=4.8,
            colors=["Brown"],
        ).model_dump(),
        Shoe(
            title="Wholecut Prestige",
            description="Single‑piece leather wholecut for a seamless silhouette",
            brand="Aristocrat",
            price=199.00,
            images=[
                "https://images.unsplash.com/photo-1521579873432-524e5b81f7ae?q=80&w=1600&auto=format&fit=crop",
            ],
            rating=4.9,
            colors=["Black"],
        ).model_dump(),
        Shoe(
            title="Wingtip Heritage",
            description="Classic brogue wingtip with hand‑stitched detailing",
            brand="Heritage",
            price=159.00,
            images=[
                "https://images.unsplash.com/photo-1614252369475-531eba34b280?q=80&w=1600&auto=format&fit=crop",
            ],
            rating=4.5,
            colors=["Brown", "Tan"],
        ).model_dump(),
    ]

    for s in sample:
        create_document("shoe", s)
    return {"seeded": True, "count": len(sample)}


# === Product Endpoints ===
@app.get("/shoes")
def list_shoes():
    docs = get_documents("shoe")
    return [to_public(d) for d in docs]


@app.get("/shoes/{shoe_id}")
def get_shoe(shoe_id: str):
    try:
        doc = db["shoe"].find_one({"_id": ObjectId(shoe_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Shoe not found")
        return to_public(doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")


# === Orders (Protected) ===
class CartItem(BaseModel):
    product_id: str
    quantity: int = 1
    size: Optional[int] = None
    color: Optional[str] = None


class CreateOrderRequest(BaseModel):
    items: List[CartItem]
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    address: Optional[str] = None


@app.post("/orders")
def create_order(payload: CreateOrderRequest, user: dict = Depends(get_current_user)):
    # Build order totals from items
    subtotal = 0.0
    order_items = []
    for item in payload.items:
        try:
            doc = db["shoe"].find_one({"_id": ObjectId(item.product_id)})
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product id")
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        price = float(doc.get("price", 0))
        subtotal += price * item.quantity
        order_items.append(
            {
                "product_id": item.product_id,
                "title": doc.get("title"),
                "price": price,
                "quantity": item.quantity,
                "size": item.size,
                "color": item.color,
                "image": (doc.get("images") or [None])[0],
            }
        )
    shipping = 0 if subtotal >= 199 else 9.99
    total = round(subtotal + shipping, 2)

    order_doc = {
        "items": order_items,
        "subtotal": round(subtotal, 2),
        "shipping": shipping,
        "total": total,
        "customer_name": payload.customer_name or user.get("name"),
        "customer_email": payload.customer_email or user.get("email"),
        "address": payload.address,
        "status": "created",
        "user_id": str(user.get("_id")),
    }

    order_id = create_document("order", order_doc)
    return {"id": order_id, **order_doc}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
