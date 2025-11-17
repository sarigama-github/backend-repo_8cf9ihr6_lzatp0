import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import Product as ProductSchema

app = FastAPI(title="Premium E‑commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True


class ProductOut(ProductCreate):
    id: str


@app.get("/")
def read_root():
    return {"message": "E‑commerce Backend Ready"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
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
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
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

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -------------------- Products Endpoints --------------------

def _product_doc_to_out(doc) -> ProductOut:
    return ProductOut(
        id=str(doc.get("_id")),
        title=doc.get("title"),
        description=doc.get("description"),
        price=float(doc.get("price", 0)),
        category=doc.get("category"),
        in_stock=bool(doc.get("in_stock", True)),
    )


@app.get("/api/products", response_model=List[ProductOut])
def list_products(category: Optional[str] = Query(None, description="Filter by category"), limit: int = Query(24, ge=1, le=100)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    filters = {}
    if category:
        filters["category"] = category
    docs = get_documents("product", filters, limit)
    return [_product_doc_to_out(d) for d in docs]


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    doc = db["product"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_doc_to_out(doc)


@app.post("/api/products", response_model=str)
def create_product(payload: ProductCreate):
    # Validate using schema
    validated = ProductSchema(**payload.model_dump())
    new_id = create_document("product", validated)
    return new_id


@app.get("/api/products/featured", response_model=List[ProductOut])
def featured_products(limit: int = Query(6, ge=1, le=24)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    docs = db["product"].find({"in_stock": True}).sort("created_at", -1).limit(limit)
    return [_product_doc_to_out(d) for d in docs]


# -------------------- Seed Sample Data on Startup --------------------
@app.on_event("startup")
async def seed_products_on_startup():
    try:
        if db is None:
            return
        count = db["product"].count_documents({})
        if count == 0:
            samples = [
                {
                    "title": "Aurora Pro Headphones",
                    "description": "Wireless noise-cancelling over‑ear with studio clarity.",
                    "price": 199.99,
                    "category": "audio",
                    "in_stock": True,
                },
                {
                    "title": "Nebula Smartwatch X",
                    "description": "AMOLED display, 7‑day battery, health suite.",
                    "price": 249.0,
                    "category": "wearables",
                    "in_stock": True,
                },
                {
                    "title": "Lumen Desk Lamp",
                    "description": "Touch dimming, USB‑C hub, minimalist aluminum.",
                    "price": 89.0,
                    "category": "home",
                    "in_stock": True,
                },
                {
                    "title": "Orbit Mechanical Keyboard",
                    "description": "Hot‑swap switches, RGB underglow, CNC chassis.",
                    "price": 159.0,
                    "category": "peripherals",
                    "in_stock": True,
                },
                {
                    "title": "Voyager Sling Bag",
                    "description": "Water‑resistant, magnetic latches, tech‑ready.",
                    "price": 79.0,
                    "category": "travel",
                    "in_stock": True,
                },
                {
                    "title": "Quanta Power Bank 20K",
                    "description": "PD 65W fast charge, slim metal body.",
                    "price": 69.0,
                    "category": "power",
                    "in_stock": True,
                },
            ]
            for s in samples:
                try:
                    validated = ProductSchema(**s)
                    create_document("product", validated)
                except Exception:
                    continue
    except Exception:
        # Silent seed failure should not break app
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
