import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'schindia_backend.settings'

import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Create the user that logged in via the frontend
email = "meghasoni2510000@gmail.com"
if not User.objects.filter(email=email).exists():
    u = User.objects.create_user(
        username=email,
        email=email,
        password="placeholder",  # won't be used - JWT handles auth
        first_name="Megha",
        last_name="Soni",
        role="root",
        status="approved",
        is_staff=True,
    )
    print(f"Created: {u.email} (id={u.id})")
else:
    u = User.objects.get(email=email)
    print(f"Already exists: {u.email} (id={u.id})")
