

from django.db import models
from userauths.models import User
import shortuuid
from shortuuid.django_fields import ShortUUIDField
from django.utils.text import slugify
from django.utils.html import mark_safe

HOTEL_STATUS=(
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('blocked', 'Blocked')
    )
 


class Hotel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image =models.FileField(upload_to='hotel_images/', blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=HOTEL_STATUS, default='pending')
    views = models.IntegerField(default=0)
    featured = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.slug == "" or self.slug is None:
            uuid_key = shortuuid.uuid()
            uniqueid = uuid_key[:8]
            self.slug = slugify(self.name) + "-" + uniqueid.lower()

        super(Hotel, self).save(*args, **kwargs)

    
    def thumbnail(self):
        return mark_safe(f'<img src="{self.image.url}" width="50px" height="50px" style="object-fit: cover;border-radius: 5px;" />')
