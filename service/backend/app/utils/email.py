import re
from typing import Tuple
from email_validator import validate_email as email_validate


def is_valid_email_format(email: str) -> bool:
    """
    Validate email format using RFC 5322 standard.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise
    """
    try:
        email_validate(email)
        return True
    except:
        return False


def normalize_email(email: str) -> str:
    """
    Normalize email address (lowercase, trim whitespace).

    Args:
        email: Email address to normalize

    Returns:
        Normalized email address
    """
    return email.strip().lower()


def extract_email_domain(email: str) -> str:
    """
    Extract domain from email address.

    Args:
        email: Email address

    Returns:
        Domain portion of email
    """
    try:
        return email.split('@')[1].lower()
    except IndexError:
        return ""
