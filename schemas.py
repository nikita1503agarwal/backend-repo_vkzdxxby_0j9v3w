"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Formal shoes specific product schema
class Shoe(BaseModel):
    """
    Formal shoes collection schema
    Collection name: "shoe"
    """
    title: str
    description: Optional[str] = None
    brand: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str = Field("formal-shoes", description="Fixed category for this app")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    rating: float = Field(4.5, ge=0, le=5)
    in_stock: bool = True
    colors: List[str] = Field(default_factory=lambda: ["Black", "Brown", "Tan"]) 
    sizes: List[int] = Field(default_factory=lambda: [6,7,8,9,10,11,12])

class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int = Field(1, ge=1)
    size: Optional[int] = None
    color: Optional[str] = None
    image: Optional[str] = None

class Order(BaseModel):
    """Orders collection schema. Collection name: "order"""
    items: List[OrderItem]
    subtotal: float = Field(..., ge=0)
    shipping: float = Field(0, ge=0)
    total: float = Field(..., ge=0)
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    address: Optional[str] = None
    status: str = Field("created", description="created, paid, shipped, delivered")
