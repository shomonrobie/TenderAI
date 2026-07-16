# utils/otp_service.py - Refactored to use CRUD methods

import random
import string
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import logging
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config.settings import Config
from database.unified_db_manager import get_db_manager
from utils.validators import validate_bangladesh_mobile, normalize_mobile

logger = logging.getLogger(__name__)
print(f"SMTP_USER: {Config.SMTP_USER}")
print(f"SMTP_PASSWORD length: {len(Config.SMTP_PASSWORD) if Config.SMTP_PASSWORD else 0}")
print(f"SMTP_PASSWORD first 4 chars: {Config.SMTP_PASSWORD[:4] if Config.SMTP_PASSWORD else 'None'}")


class OTPService:
    """Handle OTP generation, sending, and verification"""
    
    def __init__(self, db=None):
        self.db = db or get_db_manager()
        self.config = Config
    
    def generate_otp(self, length: int = None) -> str:
        """Generate numeric OTP"""
        length = length or self.config.OTP_LENGTH
        return ''.join(random.choices(string.digits, k=length))
    
    def _send_sms_ssl_wireless(self, mobile_number: str, message: str) -> bool:
        """Send SMS via SSL Wireless (Bangladesh)"""
        try:
            mobile = mobile_number
            if mobile.startswith('+88'):
                mobile = mobile[3:]
            elif mobile.startswith('88'):
                mobile = mobile[2:]
            
            response = requests.post(
                self.config.SSL_WIRELESS_URL,
                json={
                    "api_key": self.config.SSL_WIRELESS_API_KEY,
                    "sid": self.config.SSL_WIRELESS_SID,
                    "msisdn": mobile,
                    "sms": message,
                    "csms_id": secrets.token_hex(8)
                },
                timeout=10
            )
            
            return response.status_code == 200 and response.json().get('status') == 'SUCCESS'
            
        except Exception as e:
            logger.error(f"SSL Wireless SMS failed: {e}")
            return False
    
    def _send_sms_twilio(self, mobile_number: str, message: str) -> bool:
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.config.TWILIO_ACCOUNT_SID, self.config.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=message,
                from_=self.config.TWILIO_PHONE_NUMBER,
                to=mobile_number
            )
            
            return message.sid is not None
            
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return False
    
    def _send_sms_test(self, mobile_number: str, message: str) -> bool:
        """Test mode - just print to console"""
        print(f"\n{'='*50}")
        print(f"📱 SMS TO: {mobile_number}")
        print(f"📝 MESSAGE: {message}")
        print(f"{'='*50}\n")
        return True
    
    def send_sms(self, mobile_number: str, message: str) -> bool:
        """Send SMS via configured provider"""
        
        if not self.config.SMS_ENABLED:
            return self._send_sms_test(mobile_number, message)
        
        if self.config.SMS_PROVIDER == 'ssl_wireless':
            return self._send_sms_ssl_wireless(mobile_number, message)
        elif self.config.SMS_PROVIDER == 'twilio':
            return self._send_sms_twilio(mobile_number, message)
        else:
            return self._send_sms_test(mobile_number, message)
    
    def _send_email_smtp(self, email: str, subject: str, body: str) -> bool:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.config.SMTP_FROM_NAME} <{self.config.SMTP_FROM_EMAIL}>"
            msg['To'] = email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    # utils/otp_service.py - Add this debug method

    def test_email_connection(self):
        """Test email connection and send a test email"""
        print("🔍 TESTING EMAIL CONNECTION...")
        print(f"   EMAIL_ENABLED: {self.config.EMAIL_ENABLED}")
        print(f"   SMTP_HOST: {self.config.SMTP_HOST}")
        print(f"   SMTP_PORT: {self.config.SMTP_PORT}")
        print(f"   SMTP_USER: {self.config.SMTP_USER}")
        print(f"   SMTP_FROM_EMAIL: {self.config.SMTP_FROM_EMAIL}")
        
        if not self.config.EMAIL_ENABLED:
            print("❌ EMAIL_ENABLED is False")
            return False, "Email is disabled in config"
        
        if not self.config.SMTP_USER or not self.config.SMTP_PASSWORD:
            print("❌ SMTP credentials missing")
            return False, "SMTP credentials missing"
        
        # Try to send a test email
        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.config.SMTP_FROM_NAME} <{self.config.SMTP_FROM_EMAIL}>"
            msg['To'] = self.config.SMTP_USER  # Send to yourself
            msg['Subject'] = "TenderAI - Test Email"
            
            body = """
            <html>
            <body>
                <h2>✅ Test Email from TenderAI</h2>
                <p>This is a test email to verify that the SMTP configuration is working.</p>
                <p>If you receive this, email sending is properly configured!</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
            
            print(f"🔍 Connecting to {self.config.SMTP_HOST}:{self.config.SMTP_PORT}...")
            
            with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT) as server:
                server.starttls()
                print("🔍 TLS started")
                
                print(f"🔍 Logging in as {self.config.SMTP_USER}...")
                server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
                print("✅ Login successful")
                
                print(f"🔍 Sending email to {self.config.SMTP_USER}...")
                server.send_message(msg)
                print("✅ Email sent successfully!")
                
            return True, "Test email sent successfully!"
            
        except Exception as e:
            print(f"❌ Test email failed: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Test email failed: {str(e)}"
        
    def _send_email_test(self, email: str, subject: str, body: str) -> bool:
        """Test mode - just print to console"""
        print(f"\n{'='*50}")
        print(f"📧 EMAIL TO: {email}")
        print(f"📋 SUBJECT: {subject}")
        print(f"📝 BODY: {body[:200]}...")
        print(f"{'='*50}\n")
        return True
    
    def send_email(self, email: str, subject: str, body: str) -> bool:
        """Send email via configured provider"""
        
        print(f"🔍 DEBUG: send_email called")
        print(f"   EMAIL_ENABLED: {self.config.EMAIL_ENABLED}")
        print(f"   DEBUG_OTP_PRINT: {self.config.DEBUG_OTP_PRINT}")
        print(f"   SMTP_HOST: {self.config.SMTP_HOST}")
        print(f"   SMTP_PORT: {self.config.SMTP_PORT}")
        print(f"   SMTP_USER: {self.config.SMTP_USER}")
        print(f"   SMTP_FROM_EMAIL: {self.config.SMTP_FROM_EMAIL}")
        print(f"   Email: {email}")
        print(f"   Subject: {subject}")
        print(f"   Body length: {len(body)}")
        
        if not self.config.EMAIL_ENABLED or self.config.DEBUG_OTP_PRINT:
            print("🔍 DEBUG: Email disabled or debug mode - printing to console")
            return self._send_email_test(email, subject, body)
        
        print("🔍 DEBUG: Attempting to send real email via SMTP...")
        return self._send_email_smtp(email, subject, body)

    def test_gmail_connection(self):
        """Test Gmail SMTP connection"""
        print("🔍 Testing Gmail SMTP connection...")
        print(f"   SMTP_USER: {self.config.SMTP_USER}")
        print(f"   SMTP_PASSWORD: {'*' * len(self.config.SMTP_PASSWORD) if self.config.SMTP_PASSWORD else 'MISSING'}")
        print(f"   SMTP_HOST: {self.config.SMTP_HOST}")
        print(f"   SMTP_PORT: {self.config.SMTP_PORT}")
        
        if not self.config.SMTP_USER or not self.config.SMTP_PASSWORD:
            print("❌ SMTP credentials missing!")
            return False, "SMTP credentials missing"
        
        try:
            import smtplib
            print("🔍 Connecting to Gmail...")
            
            server = smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT)
            server.set_debuglevel(1)  # Show detailed debug info
            server.starttls()
            print("🔍 Logging in...")
            server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
            print("✅ Login successful!")
            server.quit()
            
            return True, "Gmail SMTP connection successful!"
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Authentication Error: {e}")
            print("   Possible causes:")
            print("   1. Wrong email or password")
            print("   2. 2-Step Verification not enabled")
            print("   3. App Password not generated correctly")
            print("   4. Email mismatch in config")
            return False, f"Authentication failed: {e}"
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return False, f"Connection failed: {e}"

    
    def send_verification_otp(self, contact_type: str, contact_value: str,
                          target_type: str, target_id: int,
                          purpose: str = 'verification') -> Tuple[bool, str, Optional[str]]:
        """
        Send OTP for verification
        Returns: (success, message, otp_code)
        """
        
        print(f"🔍 DEBUG: send_verification_otp called with contact_type={contact_type}, contact_value={contact_value}")
        
        # Validate contact value
        if contact_type == 'mobile':
            contact_value = self.normalize_mobile(contact_value)
            if not self.validate_bangladesh_mobile(contact_value):
                return False, "Invalid Bangladeshi mobile number", None
        
        # Generate OTP
        otp_code = self.generate_otp()
        print(f"🔍 DEBUG: Generated OTP: {otp_code}")
        
        expires_at = datetime.now() + timedelta(minutes=self.config.OTP_EXPIRY_MINUTES)
        
        # Invalidate old unused OTPs
        self.db.invalidate_old_otps(contact_type, contact_value, purpose)
        
        # Store OTP
        otp_id = self.db.create_otp({
            'target_type': target_type,
            'target_id': target_id,
            'contact_type': contact_type,
            'contact_value': contact_value,
            'otp_code': otp_code,
            'purpose': purpose,
            'expires_at': expires_at.isoformat()
        })
        
        print(f"🔍 DEBUG: OTP stored in database with ID: {otp_id}")
        
        # Send OTP via appropriate channel
        if contact_type == 'mobile':
            message = f"Your TenderAI verification code is: {otp_code}. Valid for {self.config.OTP_EXPIRY_MINUTES} minutes."
            success = self.send_sms(contact_value, message)
            channel = "SMS"
        else:
            subject = "TenderAI - Email Verification Code"
            body = self._generate_otp_email_body(otp_code)
            
            # ✅ Even in debug mode, try to send real email
            # If DEBUG_OTP_PRINT is True, also print to console
            if self.config.DEBUG_OTP_PRINT:
                print(f"\n{'='*50}")
                print(f"📧 EMAIL TO: {contact_value}")
                print(f"📋 SUBJECT: {subject}")
                print(f"📝 OTP CODE: {otp_code}")
                print(f"{'='*50}\n")
            
            # ✅ Always try to send real email if EMAIL_ENABLED
            if self.config.EMAIL_ENABLED:
                success = self._send_email_smtp(contact_value, subject, body)
                channel = "Email"
            else:
                success = True  # Console output counts as success in debug mode
                channel = "Console"
        
        print(f"🔍 DEBUG: {channel} send success: {success}")
        
        if success:
            logger.info(f"OTP sent via {channel} to {contact_value}")
            print(f"🔍 DEBUG: Returning OTP: {otp_code}")
            return True, f"{channel} with OTP sent to {self.mask_contact(contact_value)}", otp_code
        else:
            logger.error(f"Failed to send OTP via {channel} to {contact_value}")
            return False, f"Failed to send {channel}. Please try again.", None

    
    def _generate_otp_email_body(self, otp_code: str) -> str:
        """Generate HTML email body for OTP"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .code {{ font-size: 32px; font-weight: bold; color: #4CAF50; text-align: center; padding: 20px; }}
                .footer {{ font-size: 12px; color: #666; text-align: center; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>TenderAI Email Verification</h2>
                </div>
                <p>Hello,</p>
                <p>Your verification code is:</p>
                <div class="code">{otp_code}</div>
                <p>This code is valid for {self.config.OTP_EXPIRY_MINUTES} minutes.</p>
                <p>If you didn't request this, please ignore this email.</p>
                <div class="footer">
                    <p>Best regards,<br>TenderAI Team</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def verify_otp(self, contact_type: str, contact_value: str,
                   otp_code: str, purpose: str = 'verification') -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify OTP code
        """
        
        print(f"🔍 DEBUG: verify_otp called with contact_type={contact_type}, contact_value={contact_value}, otp_code={otp_code}, purpose={purpose}")
        
        if contact_type == 'mobile':
            contact_value = self.normalize_mobile(contact_value)
        
        # ✅ Find valid OTP using CRUD method
        try:
            otp_record = self.db.get_valid_otp(
                contact_type, contact_value, otp_code, purpose,
                self.config.OTP_MAX_ATTEMPTS
            )
            
            print(f"🔍 DEBUG: Query executed, otp_record found: {otp_record is not None}")
            if otp_record:
                print(f"🔍 DEBUG: OTP record ID: {otp_record.get('id')}")
            else:
                print("🔍 DEBUG: No valid OTP record found")
                
                # Debug: Check what OTPs exist for this contact
                check_record = self.db.get_latest_otp(contact_value, purpose)
                if check_record:
                    print(f"🔍 DEBUG: Latest OTP in DB: {check_record}")
                    print(f"🔍 DEBUG: DB OTP code: {check_record.get('otp_code')}, User entered: {otp_code}")
                    print(f"🔍 DEBUG: DB is_used: {check_record.get('is_used')}")
                    print(f"🔍 DEBUG: DB expires_at: {check_record.get('expires_at')}")
                    print(f"🔍 DEBUG: DB attempts: {check_record.get('attempts')}")
            
        except Exception as e:
            print(f"🔍 DEBUG: Database query error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Database error: {str(e)}", None
        
        if not otp_record:
            # ✅ Increment attempts using CRUD method
            try:
                self.db.increment_otp_attempts(contact_type, contact_value, purpose)
                print("🔍 DEBUG: Incremented attempts for latest OTP")
            except Exception as e:
                print(f"🔍 DEBUG: Error incrementing attempts: {e}")
            
            return False, "Invalid or expired OTP. Please request a new one.", None
        
        # ✅ Mark OTP as used using CRUD method
        try:
            self.db.mark_otp_used(otp_record['id'])
            print(f"🔍 DEBUG: OTP marked as used: {otp_record['id']}")
        except Exception as e:
            print(f"🔍 DEBUG: Error marking OTP as used: {e}")
        
        # ✅ Update verification status using CRUD method
        target_type = otp_record['target_type']
        target_id = otp_record['target_id']
        
        print(f"🔍 DEBUG: Updating verification for target_type={target_type}, target_id={target_id}")
        
        if contact_type == 'mobile':
            update_fields = {
                'mobile_verified': 1,
                'mobile_verified_at': datetime.now().isoformat()
            }
        else:
            update_fields = {
                'email_verified': 1,
                'email_verified_at': datetime.now().isoformat()
            }
        
        # Update appropriate table
        table = 'users' if target_type == 'user' else 'companies'
        
        try:
            self.db.update_verification_status(table, target_id, update_fields)
            print(f"🔍 DEBUG: Updated {table} table for id={target_id}")
        except Exception as e:
            print(f"🔍 DEBUG: Error updating {table}: {e}")
        
        # ✅ Log verification using CRUD method
        try:
            self.db.log_verification_history(
                target_type, target_id, contact_type, contact_value, 'otp'
            )
            print("🔍 DEBUG: Verification history logged")
        except Exception as e:
            print(f"🔍 DEBUG: Error logging verification history: {e}")
        
        return True, f"{contact_type.capitalize()} verified successfully!", dict(otp_record)
    
    def resend_otp(self, contact_type: str, contact_value: str,
                   target_type: str, target_id: int,
                   purpose: str = 'verification') -> Tuple[bool, str]:
        """Resend OTP - invalidate old ones first"""
        
        if contact_type == 'mobile':
            contact_value = self.normalize_mobile(contact_value)
        
        return self.send_verification_otp(contact_type, contact_value, target_type, target_id, purpose)
    
    def send_login_otp(self, mobile_number: str, user_id: int) -> Tuple[bool, str]:
        """Send OTP for login authentication"""
        return self.send_verification_otp(
            contact_type='mobile',
            contact_value=mobile_number,
            target_type='user',
            target_id=user_id,
            purpose='login'
        )
    
    def verify_login_otp(self, mobile_number: str, otp_code: str) -> Tuple[bool, str, Optional[Dict]]:
        """Verify OTP for login"""
        return self.verify_otp('mobile', mobile_number, otp_code, purpose='login')
    
    def send_password_reset_otp(self, email: str, user_id: int) -> Tuple[bool, str]:
        """Send OTP for password reset"""
        return self.send_verification_otp(
            contact_type='email',
            contact_value=email,
            target_type='user',
            target_id=user_id,
            purpose='password_reset'
        )
    
    # @staticmethod
    # def validate_bangladesh_mobile(mobile: str) -> bool:
    #     """Validate Bangladeshi mobile number"""
    #     import re
    #     mobile = re.sub(r'[\s\-+]', '', mobile)
    #     if mobile.startswith('88'):
    #         mobile = mobile[2:]
    #     pattern = r'^01[3-9]\d{8}$'
    #     return bool(re.match(pattern, mobile))
    
    # @staticmethod
    # def normalize_mobile(mobile: str) -> str:
    #     """Normalize mobile number to standard format"""
    #     import re
    #     mobile = re.sub(r'[\s\-+]', '', mobile)
    #     if mobile.startswith('+88'):
    #         mobile = mobile[3:]
    #     elif mobile.startswith('88'):
    #         mobile = mobile[2:]
    #     return mobile
    
    @staticmethod
    def mask_contact(contact: str) -> str:
        """Mask contact for display (e.g., 01*******89)"""
        if len(contact) >= 8:
            return contact[:2] + '*' * (len(contact) - 4) + contact[-2:]
        return contact