import re
from typing import Tuple


def validate_password_strength(password: str) -> Tuple[bool, list[str]]:
    """
    Validate password strength against security requirements.

    Requirements:
    - Minimum 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one number
    - At least one special character

    Args:
        password: Password string to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number")

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':\"\\|,.<>/?]', password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def get_password_strength_score(password: str) -> int:
    """
    Calculate password strength score (0-5).
    Higher score indicates stronger password.
    """
    score = 0

    # Length check
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1

    # Character variety
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':\"\\|,.<>/?]', password))

    variety_count = sum([has_lower, has_upper, has_digit, has_special])
    score += min(variety_count, 3)

    return min(score, 5)
