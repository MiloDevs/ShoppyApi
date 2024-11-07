from fastapi import FastAPI
from routes import (
    default,
    products
)
import uvicorn
from lib.db import engine, Base

# create an instance of FastAPI
app = FastAPI()

# include routes
app.include_router(default.router)
app.include_router(products.router)


# run app
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
