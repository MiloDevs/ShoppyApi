from fastapi import APIRouter, Response

# create a router
router = APIRouter()

# define route
@router.get("/")
async def home():
    return Response(content="It's aliveee", media_type="text/plain")
