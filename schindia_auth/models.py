import uuid
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils import timezone


class OTPToken(models.Model):
    """OTP token for passwordless login (Req 21)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=128)  # hashed OTP — never store plaintext
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.email} - {'used' if self.is_used else 'active'}"

    @classmethod
    def generate(cls, email):
        """Generate a new 6-digit OTP for the given email."""
        import hashlib

        # Invalidate previous unused OTPs for this email
        cls.objects.filter(email=email, is_used=False).update(is_used=True)

        # Purge expired rows older than 1 hour to prevent table bloat
        cutoff = timezone.now() - timedelta(hours=1)
        cls.objects.filter(email=email, expires_at__lt=cutoff).delete()

        code = f"{secrets.randbelow(1000000):06d}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        expires_at = timezone.now() + timedelta(minutes=5)

        otp = cls.objects.create(
            email=email,
            code_hash=code_hash,
            expires_at=expires_at,
        )
        # Attach plaintext code for sending (not persisted)
        otp._plaintext_code = code
        return otp

    @property
    def code(self):
        """Return plaintext code if available (only right after generate)."""
        return getattr(self, '_plaintext_code', None)

    def verify_code(self, code):
        """Verify a plaintext code against the stored hash."""
        import hashlib
        return self.code_hash == hashlib.sha256(code.encode()).hexdigest()

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    @classmethod
    def is_email_locked(cls, email):
        """Check lockout at the email level, not per-row."""
        locked_otp = cls.objects.filter(
            email=email,
            locked_until__gt=timezone.now(),
        ).first()
        return locked_otp is not None


class RootAccessRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # hashed
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Root Access Request'
        verbose_name_plural = 'Root Access Requests'

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.status}"

    def save(self, *args, **kwargs):
        # Hash password only if it's not already hashed
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


class User(AbstractUser):
    ROLE_CHOICES = [('root', 'Root'), ('admin', 'Admin')]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    NOTIFICATION_PREF_CHOICES = [
        ('all', 'All notifications'),
        ('milestones', 'Milestones only'),
        ('none', 'No email notifications'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='admin')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    email_verified = models.BooleanField(default=False)  # Req 21: OTP email verification
    notification_preference = models.CharField(
        max_length=15, choices=NOTIFICATION_PREF_CHOICES, default='all'
    )  # Req 25.4
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    @property
    def name(self):
        return self.get_full_name()
