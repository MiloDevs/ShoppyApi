import asyncio
import random
import aiohttp
import faker
import logging
from typing import List, Dict
from datetime import datetime
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker
fake = faker.Faker()

async def create_product(session: aiohttp.ClientSession, product_data: Dict) -> bool:
    """Create a single product via API call"""
    async with session.post('http://localhost:8000/products', json=product_data) as response:
        if response.status == 201:
            return True
        logger.error(f"Failed to create product: {await response.text()}")
        return False

def generate_product_data() -> Dict:
    """Generate random product data"""
    product_types = ['Electronics', 'Clothing', 'Books', 'Home', 'Sports']
    adjectives = ['Premium', 'Deluxe', 'Basic', 'Pro', 'Ultra']

    product_type = random.choice(product_types)
    adjective = random.choice(adjectives)

    return {
        "name": f"{adjective} {fake.word().title()} {product_type}",
        "price": random.randint(999, 99999)  # Price between $9.99 and $999.99 (stored in cents)
    }

async def batch_create_products(num_products: int):
    """Create multiple products in parallel"""
    async with aiohttp.ClientSession() as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn()
        ) as progress:

            task = progress.add_task("[cyan]Creating products...", total=num_products)
            tasks = []

            for _ in range(num_products):
                product_data = generate_product_data()
                tasks.append(create_product(session, product_data))

            results = await asyncio.gather(*tasks)
            progress.update(task, advance=num_products)

            successful = sum(1 for result in results if result)
            logger.info(f"Successfully created {successful}/{num_products} products")

def main():
    """Main entry point"""
    NUM_PRODUCTS = 50  # Change this number to create more or fewer products

    print(f"\n🚀 Starting product creation script...")
    print(f"Target: {NUM_PRODUCTS} products\n")

    start_time = datetime.now()

    # Run the async function
    asyncio.run(batch_create_products(NUM_PRODUCTS))

    duration = datetime.now() - start_time
    print(f"\n✨ Completed in {duration.total_seconds():.2f} seconds")

if __name__ == "__main__":
    main()
