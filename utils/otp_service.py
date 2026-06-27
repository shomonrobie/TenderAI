# utils/otp_service.py

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

logger = logging.getLogger(__name__)


class OTPService:
    """Handle OTP generation, sending, and verification"""
    
    def __init__(self, db):
        self.db = db
        self.config = Config
    
    def generate_otp(self, length: int = None) -> str:
        """Generate numeric OTP"""
        length = length or self.config.OTP_LENGTH
        return ''.join(random.choices(string.digits, k=length))
    
    def _send_sms_ssl_wireless(self, mobile_number: str, message: str) -> bool:
        """Send SMS via SSL Wireless (Bangladesh)"""
        try:
            # Format mobile number (remove any +88 or 88 prefix)
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
        
        if not self.config.EMAIL_ENABLED or self.config.DEBUG_OTP_PRINT:
            return self._send_email_test(email, subject, body)
        
        return self._send_email_smtp(email, subject, body)
    
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
        
        # Invalidate old unused OTPs for this contact
        self.db.execute("""
            UPDATE otp_verification
            SET is_used = 1
            WHERE contact_type = ? AND contact_value = ? AND purpose = ? AND is_used = 0
        """, (contact_type, contact_value, purpose))
        
        # Store OTP in database
        self.db.execute("""
            INSERT INTO otp_verification 
            (target_type, target_id, contact_type, contact_value, 
            otp_code, purpose, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (target_type, target_id, contact_type, contact_value, 
            otp_code, purpose, expires_at))
        
        print(f"🔍 DEBUG: OTP stored in database: {otp_code}")
        
        # Send OTP via appropriate channel
        if contact_type == 'mobile':
            message = f"Your TenderAI verification code is: {otp_code}. Valid for {self.config.OTP_EXPIRY_MINUTES} minutes."
            success = self.send_sms(contact_value, message)
            channel = "SMS"
        else:
            subject = "TenderAI - Email Verification Code"
            body = f"""
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
            success = self.send_email(contact_value, subject, body)
            channel = "Email"
        
        print(f"🔍 DEBUG: Email send success: {success}")
        
        if success:
            logger.info(f"OTP sent via {channel} to {contact_value}")
            print(f"🔍 DEBUG: Returning OTP: {otp_code}")
            return True, f"{channel} with OTP sent to {self.mask_contact(contact_value)}", otp_code
        else:
            logger.error(f"Failed to send OTP via {channel} to {contact_value}")
            return False, f"Failed to send {channel}. Please try again.", None
    
    def send_verification_otp_bak(self, contact_type: str, contact_value: str,
                              target_type: str, target_id: int,
                              purpose: str = 'verification') -> Tuple[bool, str]:
        """
        Send OTP for verification
        """
        
        # Validate contact value
        if contact_type == 'mobile':
            contact_value = self.normalize_mobile(contact_value)
            if not self.validate_bangladesh_mobile(contact_value):
                return False, "Invalid Bangladeshi mobile number"
        
        # Generate OTP
        otp_code = self.generate_otp()
        expires_at = datetime.now() + timedelta(minutes=self.config.OTP_EXPIRY_MINUTES)
        
        # Invalidate old unused OTPs for this contact
        self.db.execute("""
            UPDATE otp_verification
            SET is_used = 1
            WHERE contact_type = ? AND contact_value = ? AND purpose = ? AND is_used = 0
        """, (contact_type, contact_value, purpose))
        
        # Store OTP in database
        self.db.execute("""
            INSERT INTO otp_verification 
            (target_type, target_id, contact_type, contact_value, 
             otp_code, purpose, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (target_type, target_id, contact_type, contact_value, 
              otp_code, purpose, expires_at))
        
        # Send OTP via appropriate channel
        if contact_type == 'mobile':
            message = f"Your TenderAI verification code is: {otp_code}. Valid for {self.config.OTP_EXPIRY_MINUTES} minutes."
            success = self.send_sms(contact_value, message)
            channel = "SMS"
        else:
            subject = "TenderAI - Email Verification Code"
            body = f"""
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
            success = self.send_email(contact_value, subject, body)
            channel = "Email"
        
        if success:
            logger.info(f"OTP sent via {channel} to {contact_value}")
            return True, f"{channel} with OTP sent to {self.mask_contact(contact_value)}"
        else:
            logger.error(f"Failed to send OTP via {channel} to {contact_value}")
            return False, f"Failed to send {channel}. Please try again."
    
    def verify_otp(self, contact_type: str, contact_value: str,
                   otp_code: str, purpose: str = 'verification') -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify OTP code
        """
        
        if contact_type == 'mobile':
            contact_value = self.normalize_mobile(contact_value)
        
        # Find valid OTP
        otp_record = self.db.query_one("""
            SELECT * FROM otp_verification
            WHERE contact_type = ? 
              AND contact_value = ?
              AND otp_code = ?
              AND purpose = ?
              AND is_used = 0
              AND expires_at > CURRENT_TIMESTAMP
              AND attempts < ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (contact_type, contact_value, otp_code, purpose, self.config.OTP_MAX_ATTEMPTS))
        
        if not otp_record:
            # Increment attempts for the latest OTP
            self.db.execute("""
                UPDATE otp_verification
                SET attempts = attempts + 1
                WHERE contact_type = ? AND contact_value = ? AND purpose = ? AND is_used = 0
            """, (contact_type, contact_value, purpose))
            
            return False, "Invalid or expired OTP. Please request a new one.", None
        
        # Mark OTP as used
        self.db.execute("""
            UPDATE otp_verification
            SET is_used = 1, used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (otp_record['id'],))
        
        # Update verification status in target table
        target_type = otp_record['target_type']
        target_id = otp_record['target_id']
        
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
        
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [target_id]
        
        self.db.execute(f"""
            UPDATE {table}
            SET {set_clause}
            WHERE id = ?
        """, values)
        
        # Log verification
        self.db.execute("""
            INSERT INTO verification_history
            (target_type, target_id, contact_type, contact_value, verification_method)
            VALUES (?, ?, ?, ?, 'otp')
        """, (target_type, target_id, contact_type, contact_value))
        
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
    
    @staticmethod
    def validate_bangladesh_mobile(mobile: str) -> bool:
        """Validate Bangladeshi mobile number"""
        import re
        mobile = re.sub(r'[\s\-+]', '', mobile)
        if mobile.startswith('88'):
            mobile = mobile[2:]
        pattern = r'^01[3-9]\d{8}$'
        return bool(re.match(pattern, mobile))
    
    @staticmethod
    def normalize_mobile(mobile: str) -> str:
        """Normalize mobile number to standard format"""
        import re
        mobile = re.sub(r'[\s\-+]', '', mobile)
        if mobile.startswith('+88'):
            mobile = mobile[3:]
        elif mobile.startswith('88'):
            mobile = mobile[2:]
        return mobile
    
    @staticmethod
    def mask_contact(contact: str) -> str:
        """Mask contact for display (e.g., 01*******89)"""
        if len(contact) >= 8:
            return contact[:2] + '*' * (len(contact) - 4) + contact[-2:]
        return contact

def verify_otp(self, contact_type: str, contact_value: str,
               otp_code: str, purpose: str = 'verification') -> Tuple[bool, str, Optional[Dict]]:
    """
    Verify OTP code
    """
    
    print(f"🔍 DEBUG: verify_otp called with contact_type={contact_type}, contact_value={contact_value}, otp_code={otp_code}, purpose={purpose}")
    
    if contact_type == 'mobile':
        contact_value = self.normalize_mobile(contact_value)
    
    # Find valid OTP
    try:
        otp_record = self.db.query_one("""
            SELECT * FROM otp_verification
            WHERE contact_type = ? 
              AND contact_value = ?
              AND otp_code = ?
              AND purpose = ?
              AND is_used = 0
              AND expires_at > CURRENT_TIMESTAMP
              AND attempts < ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (contact_type, contact_value, otp_code, purpose, self.config.OTP_MAX_ATTEMPTS))
        
        print(f"🔍 DEBUG: Query executed, otp_record found: {otp_record is not None}")
        if otp_record:
            print(f"🔍 DEBUG: OTP record ID: {otp_record.get('id')}")
            print(f"🔍 DEBUG: OTP record data: {otp_record}")
        else:
            print("🔍 DEBUG: No valid OTP record found")
            
            # Debug: Check what OTPs exist for this contact
            check_record = self.db.query_one("""
                SELECT * FROM otp_verification
                WHERE contact_value = ? AND purpose = ?
                ORDER BY created_at DESC LIMIT 1
            """, (contact_value, purpose))
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
        # Increment attempts for the latest OTP
        try:
            self.db.execute("""
                UPDATE otp_verification
                SET attempts = attempts + 1
                WHERE contact_type = ? AND contact_value = ? AND purpose = ? AND is_used = 0
            """, (contact_type, contact_value, purpose))
            print("🔍 DEBUG: Incremented attempts for latest OTP")
        except Exception as e:
            print(f"🔍 DEBUG: Error incrementing attempts: {e}")
        
        return False, "Invalid or expired OTP. Please request a new one.", None
    
    # Mark OTP as used
    try:
        self.db.execute("""
            UPDATE otp_verification
            SET is_used = 1, used_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (otp_record['id'],))
        print(f"🔍 DEBUG: OTP marked as used: {otp_record['id']}")
    except Exception as e:
        print(f"🔍 DEBUG: Error marking OTP as used: {e}")
    
    # Update verification status in target table
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
    
    set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
    values = list(update_fields.values()) + [target_id]
    
    try:
        self.db.execute(f"""
            UPDATE {table}
            SET {set_clause}
            WHERE id = ?
        """, values)
        print(f"🔍 DEBUG: Updated {table} table for id={target_id}")
    except Exception as e:
        print(f"🔍 DEBUG: Error updating {table}: {e}")
    
    # Log verification
    try:
        self.db.execute("""
            INSERT INTO verification_history
            (target_type, target_id, contact_type, contact_value, verification_method)
            VALUES (?, ?, ?, ?, 'otp')
        """, (target_type, target_id, contact_type, contact_value))
        print("🔍 DEBUG: Verification history logged")
    except Exception as e:
        print(f"🔍 DEBUG: Error logging verification history: {e}")
    
    return True, f"{contact_type.capitalize()} verified successfully!", dict(otp_record)