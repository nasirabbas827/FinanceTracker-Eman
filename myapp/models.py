from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


# ==========================
# Custom User Model
# ==========================
class CustomerUser(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('banned', 'Banned'),
    )

    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255) 
    full_name = models.CharField(max_length=150, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        blank=True,
        null=True
    )
    dob = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    last_login = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

# ==========================
# Expense Model 
# ==========================
class Expense(models.Model):

    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Bills', 'Bills'),
        ('Shopping', 'Shopping'),
        ('Health', 'Health'),
        ('Education', 'Education'),
        ('Other', 'Other'),
    ]

    expense_id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        related_name='expenses'
    )

    date = models.DateField(default=timezone.now)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.category})"
    

# ==========================
# Income Model
# ==========================
class Income(models.Model):

    SOURCE_CHOICES = [
        ('Salary', 'Salary'),
        ('Business', 'Business'),
        ('Freelance', 'Freelance'),
        ('Investment', 'Investment'),
        ('Gift', 'Gift'),
        ('Other', 'Other'),
    ]

    income_id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        CustomerUser,
        on_delete=models.CASCADE,
        related_name='incomes'
    )

    date = models.DateField(default=timezone.now)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.amount} ({self.source})"