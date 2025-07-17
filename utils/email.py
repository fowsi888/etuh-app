import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def generate_reset_token():
    """Generate a random reset token"""
    length = 32
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def send_password_reset_email(to_email, temp_password):
    """Send temporary password email using the provided SMTP configuration"""
    
    # Email configuration
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_user = 'info@etuhinta.fi'
    smtp_password = 'eowl ybad mnie zwcy'
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = 'Etuhinta - Väliaikainen salasana / Temporary Password'
        
        # Email body in both Finnish and English
        body = f"""
Hei / Hello,

Olet pyytänyt salasanan palautusta Etuhinta-sovellukseen.
You have requested a password reset for the Etuhinta app.

Väliaikainen salasana / Temporary Password: {temp_password}

Kirjaudu sisään tällä väliaikaisella salasanalla ja vaihda se heti uuteen salasanaan asetuksissa.
Log in with this temporary password and change it to a new password immediately in settings.

TÄRKEÄÄ: Vaihda salasana heti kirjautumisen jälkeen!
IMPORTANT: Change your password immediately after logging in!

Jos et ole pyytänyt tätä, ota yhteyttä tukeen välittömästi.
If you did not request this, contact support immediately.

Ystävällisin terveisin / Best regards,
Etuhinta Team
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Create SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS
        server.login(smtp_user, smtp_password)
        
        # Send email
        text = msg.as_string()
        server.sendmail(smtp_user, to_email, text)
        server.quit()
        
        print(f"✅ Temporary password email sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False 