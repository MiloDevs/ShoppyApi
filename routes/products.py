import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from lib.db import Base, get_db
from pydantic import BaseModel, Field
import uuid
from sqlalchemy import Column, Integer, UUID, String, TIMESTAMP, Boolean, text
import logging
import colorama
from colorama import Fore, Style

# Initialize colorama for Windows compatibility
colorama.init()

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""

    COLORS = {
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
        'DEBUG': Fore.BLUE
    }

    def format(self, record):
        # Color the log level name if it has a color defined
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"

        # Add route information from the logger name
        route_info = record.name.split('.')[-2:]  # Gets last two parts of the logger name
        route = '.'.join(route_info)

        # Format with timestamp and route
        record.msg = f"{route} - {record.msg}"

        return super().format(record)

# Get logger
logger = logging.getLogger(__name__)  # This will include the full path e.g. 'routes.products'
logger.setLevel(logging.INFO)

# Create console handler with custom formatter
console_handler = logging.StreamHandler()
formatter = ColoredFormatter(
    fmt='%(levelname)s:  %(message)s'
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Define the model
class Product(Base):
    __tablename__ = "products"
    id = Column(UUID, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    updated_at = Column(TIMESTAMP, server_default=text("now()"))

class ProductBase(BaseModel):
    id: uuid.UUID
    name: str
    price: int = Field(gt=0, description="Price must be greater than 0")
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: int = Field(gt=0, description="Price must be greater than 0")

    class Config:
        from_attributes = True

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[int] = Field(None, gt=0, description="Price must be greater than 0")

    class Config:
        from_attributes = True

# Create the API router
router = APIRouter()

# Get all products
@router.get("/products", response_model=list[ProductBase], status_code=status.HTTP_200_OK)
async def get_products(page: int = 1, limit: int = 10, offset: int = 0, order_by: str = "created_at", db: Session = Depends(get_db)):
    try:
        products = db.query(Product).order_by(order_by).limit(limit).offset(offset).all()
        if not products:
            logger.warn("No products found")
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="No products found"
            )
        logger.info(f"Retrieved {len(products)} products successfully")
        return products
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving products"
        )

# Get a product by ID
@router.get("/products/{product_id}", response_model=ProductBase, status_code=status.HTTP_200_OK)
async def get_product(product_id: str, db: Session = Depends(get_db)):
    try:
        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(product_id)
        except ValueError:
            logger.error(f"Invalid UUID format: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product ID format"
            )

        product = db.query(Product).filter(Product.id == uuid_obj).first()
        if not product:
            logger.warning(f"Product not found with ID: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        logger.info(f"Retrieved product successfully: {product_id}")
        return product
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching product {product_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving product"
        )

# Create a product
@router.post("/products", response_model=ProductBase, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    try:
        new_product = Product(
            id=uuid.uuid4(),
            name=product.name,
            price=product.price
        )
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        logger.info(f"Created new product successfully: {new_product.id}")
        return new_product
    except IntegrityError as e:
        logger.error(f"Integrity error while creating product: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product creation failed due to constraint violation"
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error while creating product: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating product"
        )

# Update a product
@router.patch("/products/{product_id}", response_model=ProductBase, status_code=status.HTTP_200_OK)
async def update_product(product_id: str, product: ProductUpdate, db: Session = Depends(get_db)):
    try:
        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(product_id)
        except ValueError:
            logger.error(f"Invalid UUID format: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product ID format"
            )

        product_to_update = db.query(Product).filter(Product.id == uuid_obj).first()
        if not product_to_update:
            logger.warning(f"Product not found for update: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Update only provided fields
        update_data = product.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )

        for key, value in update_data.items():
            setattr(product_to_update, key, value)

        # Update the updated_at timestamp
        product_to_update.updated_at = datetime.datetime.now()

        db.commit()
        db.refresh(product_to_update)

        logger.info(f"Updated product successfully: {product_id}")
        return product_to_update
    except IntegrityError as e:
        logger.error(f"Integrity error while updating product {product_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product update failed due to constraint violation"
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error while updating product {product_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating product"
        )

# Delete a product
@router.delete("/products/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: str, db: Session = Depends(get_db)):
    try:
        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(product_id)
        except ValueError:
            logger.error(f"Invalid UUID format: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product ID format"
            )

        product_to_delete = db.query(Product).filter(Product.id == uuid_obj).first()
        if not product_to_delete:
            logger.warning(f"Product not found for deletion: {product_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        db.delete(product_to_delete)
        db.commit()

        return {"message": "Product deleted successfully"}

        logger.info(f"Deleted product successfully: {product_id}")
    except SQLAlchemyError as e:
        logger.error(f"Database error while deleting product {product_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting product"
        )
