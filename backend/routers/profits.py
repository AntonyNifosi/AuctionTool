"""
Profits API Router - Craft profit analysis
"""
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Query
from typing import List, Optional

from ..data_manager import get_data_manager

router = APIRouter()

# Profession ID mapping
PROFESSIONS = {
    164: "Forge",
    165: "Travail du cuir",
    171: "Alchimie",
    197: "Couture",
    202: "Ingénierie",
    333: "Enchantement",
    755: "Joaillerie",
    773: "Calligraphie",
}

# Profession names (FR) - ordered longest first to avoid partial matches
_PROFESSION_NAMES_FR = [
    "travail du cuir",  # Must be before shorter names
    "enchantement",
    "calligraphie",
    "ingénierie",
    "joaillerie",
    "alchimie",
    "couture",
    "forge",
]

# Prepositions that connect profession to expansion (with both apostrophe types)
_PREPOSITIONS = [" de ", " des ", " du ", " d'", " d\u2019"]


def _strip_profession(text: str) -> str:
    """Strip profession name and preposition from a tier name to get the expansion"""
    lower = text.lower().replace("\u2019", "'")  # Normalize typographic apostrophe
    
    for prof in _PROFESSION_NAMES_FR:
        if lower.startswith(prof):
            remainder = text[len(prof):]
            remainder_lower = remainder.lower().replace("\u2019", "'")
            
            # Try stripping preposition (e.g. "Forge d'Ombreterre" → "Ombreterre")
            for prep in [" de ", " des ", " du ", " d'"]:
                if remainder_lower.startswith(prep):
                    result = remainder[len(prep):].strip()
                    if result:
                        return result
            
            # No preposition — just strip profession name (e.g. "Forge classique" → "Classique")
            remainder = remainder.strip()
            if remainder:
                return remainder[0].upper() + remainder[1:]
            return text
    
    return text


def extract_expansion_name(tier_name: str) -> str:
    """Extract clean expansion name from tier name by stripping profession patterns.
    
    Handles formats:
    - "Forge d'Ombreterre" → "Ombreterre"
    - "Alchimie classique" → "Classique"
    - "Alchimie de Kul Tiras / Alchimie de Zandalar" → "Kul Tiras / Zandalar"
    - "Cataclysm" → "Cataclysm" (no profession, returned as-is)
    """
    if not tier_name:
        return ""
    
    cleaned = tier_name.strip()
    
    if " / " in cleaned:
        parts = cleaned.split(" / ", 1)
        part1 = _strip_profession(parts[0].strip())
        part2 = _strip_profession(parts[1].strip())
        return f"{part1} / {part2}"
    
    # Standard format
    return _strip_profession(cleaned)


@router.get("")
async def get_craft_profits(
    realm_id: int = Query(..., description="Realm ID"),
    professions: Optional[str] = Query(None, description="Comma-separated profession IDs"),
    expansion: Optional[str] = Query(None, description="Filter by single expansion (deprecated)"),
    expansions: Optional[str] = Query(None, description="Comma-separated expansion names"),
    min_profit: int = Query(0, ge=0, description="Minimum profit in copper"),
    min_volume: int = Query(0, ge=0, description="Minimum sales (3d)"),
    sort_by: str = Query("profit", description="Sort by: profit, profit_margin, name, sell_price, craft_cost, volume"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200)
):
    """Get craftable items with profit analysis"""
    dm = get_data_manager()
    
    # Parse profession IDs
    profession_ids = None
    if professions:
        try:
            profession_ids = [int(p) for p in professions.split(",")]
        except ValueError:
            pass
            
    # Parse expansion list
    expansion_list = []
    if expansions:
        expansion_list = [e.strip() for e in expansions.split(",") if e.strip()]
    elif expansion:
        # Backward compatibility with single expansion
        expansion_list = [expansion]
    
    # Get profit data (Optimized with SQL filtering)
    items = dm.get_craftable_items_profit(realm_id, profession_ids, expansion_list)
    
    # Filter by minimum profit
    if min_profit > 0:
        items = [
            item for item in items
            if (item.get("profit") or 0) >= min_profit
        ]
    
    # Filter by minimum volume
    if min_volume > 0:
        items = [
            item for item in items
            if (item.get("volume") or 0) >= min_volume
        ]
    
    # Sort with proper direction
    # Note: None values should ALWAYS be at the end (least interesting)
    reverse = sort_order == "desc"
    
    def sort_with_none_at_end(items_list, key_field, rev):
        """Sort items with None values always at the end"""
        with_value = [i for i in items_list if i.get(key_field) is not None]
        without_value = [i for i in items_list if i.get(key_field) is None]
        sorted_with = sorted(with_value, key=lambda x: x.get(key_field) or 0, reverse=rev)
        return sorted_with + without_value
    
    if sort_by == "profit":
        items = sort_with_none_at_end(items, "profit", reverse)
    elif sort_by == "profit_margin":
        items = sort_with_none_at_end(items, "profit_margin", reverse)
    elif sort_by == "sell_price":
        items = sort_with_none_at_end(items, "min_price", reverse)
    elif sort_by == "craft_cost":
        items = sort_with_none_at_end(items, "craft_cost", reverse)
    elif sort_by == "name":
        items = sorted(items, key=lambda x: (x.get("name") or "").lower(), reverse=reverse)
    elif sort_by == "volume":
        items = sort_with_none_at_end(items, "volume", reverse)
    elif sort_by == "score" or sort_by == "total_score":
        items = sort_with_none_at_end(items, "score", reverse)
    
    # Pagination
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = items[start:end]
    
    return {
        "items": paginated,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/professions")
async def get_professions():
    """Get list of available professions"""
    return {
        "professions": [
            {"id": pid, "name": name}
            for pid, name in PROFESSIONS.items()
        ]
    }


@router.get("/expansions")
async def get_expansions(realm_id: int = Query(...)):
    """Get available expansions that have craftable items"""
    dm = get_data_manager()
    
    # Get raw expansion (tier) names from DB
    raw_expansions = dm.get_all_expansions()
    
    # Clean: strip profession names to extract just the expansion/zone name
    expansions = set()
    for raw_exp in raw_expansions:
        cleaned = extract_expansion_name(raw_exp)
        if cleaned:
            expansions.add(cleaned)
    
    return {"expansions": sorted(expansions)}
