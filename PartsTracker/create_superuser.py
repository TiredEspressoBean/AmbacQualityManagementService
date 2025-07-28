import os
from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line

User = get_user_model()

if not User.objects.filter(username=os.environ["DJANGO_SUPERUSER_USERNAME"]).exists():
    username = os.environ["DJANGO_SUPERUSER_USERNAME"]
    password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
    User.objects.create_superuser(
        username=os.environ["DJANGO_SUPERUSER_USERNAME"],
        email=os.environ["DJANGO_SUPERUSER_EMAIL"],
        password=os.environ["DJANGO_SUPERUSER_PASSWORD"],
        first_name="John",
        last_name="Doe",
    )
    print(f"Superuser created successfully with username: {username} and password: {password}")