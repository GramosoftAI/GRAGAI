"""Test utilities and helpers"""
from faker import Faker

fake = Faker()


def create_test_user_data():
    """Generate test user data"""
    return {
        "email": fake.email(),
        "username": fake.user_name()[:20],
        "password": "TestPassword123!"
    }


def create_test_tenant_data():
    """Generate test tenant data"""
    return {
        "name": fake.company(),
        "slug": fake.slug()
    }
