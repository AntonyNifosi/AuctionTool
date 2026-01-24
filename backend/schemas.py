"""
Pydantic schemas for API request/response models
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RealmBase(BaseModel):
    id: int
    name: str
    population: Optional[str] = None
    region: Optional[str] = None


class RealmResponse(RealmBase):
    class Config:
        from_attributes = True


class ItemBase(BaseModel):
    item_id: int
    name: str
    icon_url: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None


class ItemSummary(ItemBase):
    min_price: Optional[int] = None
    avg_price: Optional[float] = None
    total_quantity: Optional[int] = None
    auction_count: Optional[int] = None
    sales_3d: Optional[int] = 0
    trend: Optional[float] = None
    volume_change: Optional[int] = None
    recorded_at: Optional[str] = None
    profession_name: Optional[str] = None
    craft_cost: Optional[int] = None


class ItemListResponse(BaseModel):
    items: List[ItemSummary]
    total: int
    page: int
    page_size: int


class PriceHistory(BaseModel):
    recorded_at: str
    min_price: int
    avg_price: float
    total_quantity: int
    auction_count: int
    estimated_sales: Optional[int] = 0


class ItemDetail(ItemBase):
    current_price: Optional[int] = None
    trend: Optional[float] = None
    volume_change: Optional[int] = None
    price_history: List[PriceHistory] = []
    reagents: List["Reagent"] = []


class Reagent(BaseModel):
    item_id: int
    name: str
    quantity: int
    icon_url: Optional[str] = None
    unit_price: Optional[int] = None


class RealmPrice(BaseModel):
    realm_id: int
    realm_name: str
    region: Optional[str] = None
    min_price: Optional[int] = None
    avg_price: Optional[float] = None
    total_quantity: Optional[int] = None
    recorded_at: Optional[str] = None


class ProfitItem(BaseModel):
    item_id: int
    name: str
    icon_url: Optional[str] = None
    profession_id: int
    profession_name: str
    expansion: Optional[str] = None
    craft_cost: Optional[int] = None
    sell_price: Optional[int] = None
    profit: Optional[int] = None
    profit_margin: Optional[float] = None
    volume: Optional[int] = None
    score: Optional[float] = None


class PetSummary(BaseModel):
    pet_id: int
    name: str
    icon_url: Optional[str] = None
    creature_type: Optional[str] = None
    source: Optional[str] = None
    is_tradable: bool = False
    min_price: Optional[int] = None
    sales_3d: Optional[int] = 0
    quality: Optional[str] = None


class UpdateStatus(BaseModel):
    is_running: bool
    progress: float
    status_message: str
    last_update_time: Optional[str] = None
