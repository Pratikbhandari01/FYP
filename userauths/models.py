from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
import shortuuid
from django.db.models.signals import post_save

# Create your models here.
GENDER_CHOICES = (
    ("Female", "Female"),
    ("Male", "Male"),
    ("Others", "Others"),
)

IDENTITY_TYPE = (
    ("Passport", "Passport"),
    ("Driver's License", "Driver's License"),
    ("National ID", "National ID"),
)


def user_directory_path(instance, filename):
    ext =filename.split('.')[-1]
    filename = "%s.%s" %(instance.user.id, filename)
    return "user_{0}/{1}".format(instance.user.id, filename)

class User(AbstractUser):
    ROLE_CHOICES = (
        ("customer", "Customer"),
        ("agent", "Agent"),
    )
    full_name = models.CharField(max_length=255, blank=True, null=True )
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="Others")
    otp = models.CharField(max_length=10, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="customer")

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]   # ✅ username हटायो


    def __str__(self):
        return self.full_name or self.username
    
class Profile(models.Model):
    pid = models.CharField(max_length=25, unique=True, default=shortuuid.uuid)
    image = models.FileField(upload_to =user_directory_path,default = "default.png", blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True, null=True )
    phone = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="Others")

    country = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    identity_type = models.CharField(max_length=20, choices=IDENTITY_TYPE, blank=True, null=True)
    identity_image= models.FileField(upload_to=user_directory_path, blank=True, null=True)
    wallet = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    verified = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        if self.full_name:
            return self.full_name
        else:
            return self.user.username
            
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    profile, profile_created = Profile.objects.get_or_create(user=instance)
    if not profile_created:
        profile.save()