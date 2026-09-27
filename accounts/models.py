from django.db import models
from django.db.models.functions import Lower
from django.contrib.auth.models import AbstractUser, BaseUserManager

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email field must be set.")

        email = self.normalize_email(email.strip()).lower()
        user = self.model(
            email=email,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("SuperUser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("SuperUser must have is_super=True.")
        
        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )
    
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_email_case_insensitive",
            )
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()