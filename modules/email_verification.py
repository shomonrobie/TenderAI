"""
Email Verification Module
Send OTP and verification links via email
"""

import streamlit as st
import smtplib
import random
import hashlib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

# Email configuration (use environment variables in production)
SMTP_CONFIG = {
    'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'port': int(os.getenv('SMTP_PORT', 587)),
    'username': os.getenv('SMTP_USERNAME', ''),
    'password': os.getenv('SMTP_PASSWORD', ''),
    'from_email': os.getenv('FROM_EMAIL', 'noreply@tenderai.com')
}

# Store OTPs temporarily (in production, use Redis or database)
otp_store = {}
verification_tokens = {}

def generate_otp(length=6):
    """Generate numeric OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

def generate_verification_token(email):
    """Generate unique verification token"""
    token = secrets.token_urlsafe(32)
    verification_tokens[token] = {
        'email': email,
        'expires_at': datetime.now() + timedelta(hours=24)
    }
    return token

def send_email(to_email, subject, body_html, body_text=None):
    """Send email using SMTP"""
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = SMTP_CONFIG['from_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach text version
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        
        # Attach HTML version
        msg.attach(MIMEText(body_html, 'html'))
        
        # Send email
        server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
        server.starttls()
        server.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def send_verification_email(email, username, verification_type='signup'):
    """Send verification email with OTP and link"""
    
    otp = generate_otp()
    token = generate_verification_token(email)
    
    # Store OTP with expiry
    otp_store[email] = {
        'otp': otp,
        'expires_at': datetime.now() + timedelta(minutes=15),
        'type': verification_type
    }
    
    verification_link = f"https://your-app.streamlit.app?verify={token}"
    
    if verification_type == 'signup':
        subject = "Welcome to TenderAI - Verify Your Email"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #1e3c72; text-align: center; padding: 20px; letter-spacing: 5px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to TenderAI!</h1>
                </div>
                <div class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>Thank you for registering with TenderAI. Please verify your email address to complete your registration.</p>
                    
                    <p><strong>Your Verification Code:</strong></p>
                    <div class="otp-code">{otp}</div>
                    
                    <p>Or click the button below:</p>
                    <p style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </p>
                    
                    <p>This code will expire in <strong>15 minutes</strong>.</p>
                    
                    <hr>
                    
                    <p><strong>What's Next?</strong><br>
                    After verification, our team will review your application and notify you via email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 TenderAI. All rights reserved.</p>
                    <p>Building better bids, together.</p>
                </div>
            </div>
        </body>
        </html>
        """
    else:
        subject = "TenderAI - Login Verification Code"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 20px; text-align: center; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #1e3c72; text-align: center; padding: 20px; letter-spacing: 5px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Login Verification</h1>
                </div>
                <div class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>Use the following code to complete your login:</p>
                    <div class="otp-code">{otp}</div>
                    <p>This code will expire in <strong>15 minutes</strong>.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 TenderAI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    return send_email(email, subject, html_body)

def verify_otp(email, entered_otp):
    """Verify OTP"""
    if email not in otp_store:
        return False, "No verification code found. Please request a new one."
    
    otp_data = otp_store[email]
    
    if datetime.now() > otp_data['expires_at']:
        del otp_store[email]
        return False, "Verification code has expired. Please request a new one."
    
    if otp_data['otp'] == entered_otp:
        del otp_store[email]
        return True, "Email verified successfully!"
    
    return False, "Invalid verification code. Please try again."

def verify_token(token):
    """Verify email verification token"""
    if token in verification_tokens:
        token_data = verification_tokens[token]
        if datetime.now() < token_data['expires_at']:
            return True, token_data['email']
        else:
            del verification_tokens[token]
    return False, None
def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    """Send password reset email with secure link"""
    subject = "🔑 Reset Your iTender Password"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>Password Reset Request</h2>
        <p>Hello,</p>
        <p>You requested to reset your password for your iTender account.</p>
        <p style="margin: 30px 0;">
            <a href="{reset_link}" 
               style="background-color: #1e3c72; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Reset My Password
            </a>
        </p>
        <p><strong>This link will expire in 60 minutes.</strong></p>
        <p>If you didn't request this, please ignore this email.</p>
        <hr>
        <p style="font-size: 0.9em; color: #666;">
            iTender - Tender Management System<br>
            Bangladesh
        </p>
    </body>
    </html>
    """
    
    body_text = f"""
    Password Reset Request
    
    You requested to reset your password.
    Click here to reset: {reset_link}
    
    This link expires in 60 minutes.
    If you didn't request this, ignore this email.
    """
    
    return send_email(to_email, subject, body_html, body_text)