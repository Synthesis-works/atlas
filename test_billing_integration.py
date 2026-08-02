import os
import sys
sys.path.insert(0, os.path.abspath("packages/database"))
import uuid
import asyncio
from decimal import Decimal

# Set up env vars for the script
os.environ["DATABASE_URL"] = "sqlite:///./atlas.db"

# We must mock settings before importing apps
from apps.backend.config import settings
# Razorpay keys should be picked up from .env, but let's ensure they are loaded
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from atlas_db.core.base import Base
from atlas_db.models.core import Organization
from atlas_db.models.billing import Product, Price, BillingCycle, PaymentProvider
from services.billing.checkout import create_checkout_session
from atlas_db.repositories.billing import BillingRepository

def main():
    print("Testing Razorpay Integration...")
    
    # Setup DB
    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # 1. Create a dummy organization
        org = Organization(name="Test Org", slug=f"test-org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        
        # 2. Create a Product
        product = Product(name="Atlas Pro", description="Premium tier", is_active=True)
        session.add(product)
        session.flush()
        
        # 3. Create a Price (e.g. 999 INR)
        price = Price(
            product_id=product.id,
            name="Monthly INR",
            amount=Decimal("999.00"),
            currency="INR",
            billing_cycle=BillingCycle.MONTHLY,
            is_active=True
        )
        session.add(price)
        session.flush()
        
        print(f"Created Org: {org.id}")
        print(f"Created Product: {product.id}")
        print(f"Created Price: {price.id}")
        
        # 4. Test Checkout for Razorpay
        print("\nInitiating Razorpay Checkout...")
        result = create_checkout_session(
            session=session,
            org_id=org.id,
            price_id=price.id,
            provider=PaymentProvider.RAZORPAY,
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
        )
        
        print("\n--- Checkout Result ---")
        print(f"Session / Order ID: {result.session_id}")
        print(f"URL: {result.url}")
        print("-----------------------")
        
        # 5. Check the Payment record
        repo = BillingRepository(session)
        payment = repo.get_payment_by_provider_id(result.session_id)
        if payment:
            print("\nPayment record created successfully:")
            print(f"  Payment ID: {payment.id}")
            print(f"  Amount: {payment.amount} {payment.currency}")
            print(f"  Status: {payment.status}")
        else:
            print("\nError: Payment record not found!")

        session.commit()
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
