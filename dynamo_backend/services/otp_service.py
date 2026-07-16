"""DynamoDB service for OTP-based login/password-reset tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta

from ..service import DynamoDBService
from ..tables import OTP_TOKENS_TABLE


class OtpDynamoService:
    def __init__(self):
        self.db = DynamoDBService(OTP_TOKENS_TABLE)

    def generate(self, email):
        """Generate a new 6-digit OTP for the given email.

        Invalidates previous unused OTPs for this email and purges rows
        older than 1 hour, mirroring the old OTPToken.generate() behaviour.
        """
        now = datetime.utcnow()

        for existing in self.db.query_by_index('email-index', 'email', email):
            if existing.get('is_used'):
                continue
            expires_at = existing.get('expires_at')
            if expires_at and expires_at < (now - timedelta(hours=1)).isoformat():
                self.db.delete(existing['id'])
            else:
                self.db.update(existing['id'], {'is_used': True})

        code = f"{secrets.randbelow(1000000):06d}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()

        otp = self.db.create({
            'email': email,
            'code_hash': code_hash,
            'attempts': 0,
            'is_used': False,
            'expires_at': (now + timedelta(minutes=5)).isoformat(),
            'locked_until': None,
        })
        otp['_plaintext_code'] = code
        return otp

    def get_latest_unused(self, email):
        """Return the most recent unused OTP row for this email, if any."""
        rows = [r for r in self.db.query_by_index('email-index', 'email', email) if not r.get('is_used')]
        rows.sort(key=lambda r: r.get('created_at', ''), reverse=True)
        return rows[0] if rows else None

    def is_email_locked(self, email):
        """Check lockout at the email level, not per-row."""
        now_iso = datetime.utcnow().isoformat()
        for row in self.db.query_by_index('email-index', 'email', email):
            locked_until = row.get('locked_until')
            if locked_until and locked_until > now_iso:
                return True
        return False

    def is_expired(self, otp):
        return datetime.utcnow().isoformat() > otp.get('expires_at', '')

    def verify_code(self, otp, code):
        return otp.get('code_hash') == hashlib.sha256(code.encode()).hexdigest()

    def mark_used(self, otp_id):
        return self.db.update(otp_id, {'is_used': True})

    def register_failed_attempt(self, otp):
        """Increment attempts; lock the OTP for 15 minutes after 3 failures. Returns the updated row."""
        attempts = otp.get('attempts', 0) + 1
        updates = {'attempts': attempts}
        if attempts >= 3:
            updates['locked_until'] = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            updates['is_used'] = True
        return self.db.update(otp['id'], updates)
