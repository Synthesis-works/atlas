import os
import sys
from decimal import Decimal
import logging

sys.path.insert(0, os.path.abspath("packages/database"))
from apps.backend.config import settings
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from atlas_db.models.billing import Product, Price, BillingCycle

logger = logging.getLogger(__name__)

def seed_billing():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        print("Seeding billing products...")
        
        # Atlas Free
        free_prod = session.scalar(select(Product).where(Product.name == "Atlas Free"))
        if not free_prod:
            free_prod = Product(name="Atlas Free", description="Basic features for everyone", is_active=True)
            session.add(free_prod)
            session.flush()
            
            free_price = Price(
                product_id=free_prod.id,
                name="Free",
                amount=Decimal("0.00"),
                currency="INR",
                billing_cycle=BillingCycle.MONTHLY,
                is_active=True
            )
            session.add(free_price)
            
        # Atlas Pro
        pro_prod = session.scalar(select(Product).where(Product.name == "Atlas Pro"))
        if not pro_prod:
            pro_prod = Product(name="Atlas Pro", description="Advanced platform features", is_active=True)
            session.add(pro_prod)
            session.flush()
            
            pro_monthly = Price(
                product_id=pro_prod.id,
                name="Pro Monthly",
                amount=Decimal("999.00"),
                currency="INR",
                billing_cycle=BillingCycle.MONTHLY,
                is_active=True
            )
            session.add(pro_monthly)
            
            pro_annual = Price(
                product_id=pro_prod.id,
                name="Pro Annual",
                amount=Decimal("9999.00"),
                currency="INR",
                billing_cycle=BillingCycle.YEARLY,
                is_active=True
            )
            session.add(pro_annual)

        # Atlas Enterprise
        ent_prod = session.scalar(select(Product).where(Product.name == "Atlas Enterprise"))
        if not ent_prod:
            ent_prod = Product(name="Atlas Enterprise", description="Custom solutions and limits", is_active=True)
            session.add(ent_prod)
            
        session.commit()
        print("Seeding completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Error seeding billing models: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_billing()
