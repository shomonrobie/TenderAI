# utils/validators.py

import re
import streamlit as st

def validate_password_strength(password):
    """
    Validate password strength and return score, message, and color
    
    Returns:
        tuple: (score, message, color)
    """
    score = 0
    messages = []
    
    if len(password) >= 8:
        score += 25
    else:
        messages.append("At least 8 characters")
    
    if re.search(r'[A-Z]', password):
        score += 25
    else:
        messages.append("At least one uppercase letter")
    
    if re.search(r'[a-z]', password):
        score += 25
    else:
        messages.append("At least one lowercase letter")
    
    if re.search(r'[0-9]', password):
        score += 25
    else:
        messages.append("At least one number")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 0  # Bonus for special characters
        messages.append("At least one special character")
    
    # Determine strength level
    if score >= 80:
        message = "Strong password"
        color = "#4CAF50"  # Green
    elif score >= 60:
        message = "Good password"
        color = "#FFC107"  # Yellow
    elif score >= 40:
        message = "Fair password"
        color = "#FF9800"  # Orange
    else:
        message = "Weak password"
        color = "#F44336"  # Red
    
    return score, message, color


def validate_individual_registration(full_name, username, email, mobile, password, confirm_password, terms):
    """
    Validate individual registration form data
    
    Returns:
        list: List of error messages
    """
    errors = []
    
    if not full_name:
        errors.append("Full name is required")
    elif len(full_name) < 2:
        errors.append("Full name must be at least 2 characters")
    
    if not username:
        errors.append("Username is required")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters")
    elif not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append("Username can only contain letters, numbers, and underscores")
    
    if not email:
        errors.append("Email address is required")
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors.append("Invalid email address format")
    
    if not mobile:
        errors.append("Mobile number is required")
    elif not validate_bangladesh_mobile(mobile):
        errors.append("Invalid Bangladeshi mobile number (must be 11 digits starting with 01)")
    
    if not password:
        errors.append("Password is required")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters")
    
    if not confirm_password:
        errors.append("Please confirm your password")
    elif password and confirm_password and password != confirm_password:
        errors.append("Passwords do not match")
    
    if not terms:
        errors.append("You must agree to the Terms of Service and Privacy Policy")
    
    return errors


def validate_company_registration(company_name, company_email, company_mobile, division, district,
                                  full_name, username, admin_mobile, email, password, confirm_password, terms):
    """
    Validate company registration form data
    
    Returns:
        list: List of error messages
    """
    errors = []
    
    # Company validation
    if not company_name:
        errors.append("Company name is required")
    
    if not company_email:
        errors.append("Company email is required")
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', company_email):
        errors.append("Invalid company email address format")
    
    if not company_mobile:
        errors.append("Company mobile number is required")
    elif not validate_bangladesh_mobile(company_mobile):
        errors.append("Invalid company mobile number (must be 11 digits starting with 01)")
    
    if not division:
        errors.append("Division is required")
    
    if not district:
        errors.append("District is required")
    
    # Admin validation
    if not full_name:
        errors.append("Admin full name is required")
    elif len(full_name) < 2:
        errors.append("Admin full name must be at least 2 characters")
    
    if not username:
        errors.append("Admin username is required")
    elif len(username) < 3:
        errors.append("Admin username must be at least 3 characters")
    elif not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append("Username can only contain letters, numbers, and underscores")
    
    if not admin_mobile:
        errors.append("Admin mobile number is required")
    elif not validate_bangladesh_mobile(admin_mobile):
        errors.append("Invalid admin mobile number (must be 11 digits starting with 01)")
    
    if not email:
        errors.append("Admin email address is required")
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors.append("Invalid admin email address format")
    
    if not password:
        errors.append("Admin password is required")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters")
    
    if not confirm_password:
        errors.append("Please confirm your password")
    elif password and confirm_password and password != confirm_password:
        errors.append("Passwords do not match")
    
    if not terms:
        errors.append("You must agree to the Terms of Service and Privacy Policy")
    
    return errors


def validate_bangladesh_mobile(mobile):
    """
    Validate Bangladeshi mobile number
    
    Args:
        mobile: Mobile number string
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not mobile:
        return False
    
    # Remove any spaces, dashes, or plus signs
    mobile = re.sub(r'[\s\-+]', '', mobile)
    
    # Remove country code if present
    if mobile.startswith('88'):
        mobile = mobile[2:]
    elif mobile.startswith('00'):
        mobile = mobile[2:]
    
    # Check if it's a valid Bangladeshi mobile number
    # Format: 01 followed by 3-9, then 8 digits
    pattern = r'^01[3-9]\d{8}$'
    return bool(re.match(pattern, mobile))


def normalize_mobile(mobile):
    """
    Normalize mobile number to standard format (remove spaces, dashes, country codes)
    
    Args:
        mobile: Mobile number string
    
    Returns:
        str: Normalized mobile number
    """
    if not mobile:
        return ""
    
    # Remove any spaces, dashes, or plus signs
    mobile = re.sub(r'[\s\-+]', '', mobile)
    
    # Remove country code if present
    if mobile.startswith('88'):
        mobile = mobile[2:]
    elif mobile.startswith('00'):
        mobile = mobile[2:]
    
    return mobile


def validate_username(username):
    """
    Validate username format
    
    Args:
        username: Username string
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 30:
        return False, "Username must be at most 30 characters"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, ""


def validate_email(email):
    """
    Validate email format
    
    Args:
        email: Email string
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, "Invalid email address format"
    
    return True, ""


def validate_password(password):
    """
    Validate password strength
    
    Args:
        password: Password string
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, ""


def mask_contact(contact):
    """
    Mask contact for display (e.g., 01*******89)
    
    Args:
        contact: Contact string (mobile or email)
    
    Returns:
        str: Masked contact
    """
    if not contact:
        return ""
    
    if '@' in contact:
        # Email masking
        parts = contact.split('@')
        if len(parts) == 2:
            username, domain = parts
            if len(username) <= 2:
                masked_username = username[0] + '*' * (len(username) - 1)
            else:
                masked_username = username[:2] + '*' * (len(username) - 2)
            return f"{masked_username}@{domain}"
        return contact
    else:
        # Mobile masking
        if len(contact) >= 8:
            return contact[:2] + '*' * (len(contact) - 4) + contact[-2:]
        return contact