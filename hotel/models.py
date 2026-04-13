
from decimal import Decimal

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
    ('blocked', 'Blocked'),
    ('live', 'Live')
    )

ICON_TYPE =(
    ("Bootstrap Icons ", "Bootstrap Icons"),
    ("Font Awesome", "Font Awesome"),
    ("Material Icons", "Material Icons"),
    ("Flat Icons", "Flat Icons"),
)
 


class Hotel(models.Model):
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hotels", null=True, blank=True)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='hotel_images/', blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=HOTEL_STATUS, default='pending')
    views = models.IntegerField(default=0)
    featured = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
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
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="50px" height="50px" style="object-fit: cover;border-radius: 5px;" />')
        return "No Image"

    def average_rating(self):
        aggregate = self.reviews.aggregate(avg=models.Avg('rating'))
        return round(aggregate.get('avg') or 0, 1)

    def reviews_count(self):
        return self.reviews.count()








class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    no_of_beds = models.IntegerField(default=1)
    hid = ShortUUIDField(length=8, unique=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='hotel_images/', blank=True, null=True)


    def __str__(self):
        return f"{self.name} - {self.hotel.name} - {self.price}"
    
    class Meta:
        verbose_name_plural = "Room Types"

    
    def rooms_count(self):
        return Room.objects.filter(room_type=self).count()
    
    def save(self, *args, **kwargs):
        if self.slug == "" or self.slug is None:
            uuid_key = shortuuid.uuid()
            uniqueid = uuid_key[:8]
            self.slug = slugify(self.name) + "-" + uniqueid.lower()

        super(RoomType, self).save(*args, **kwargs)

class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    availability = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    date = models.DateTimeField(auto_now_add=True)
    rid = ShortUUIDField(length=8, unique=True, blank=True)

    def __str__(self):
        return f"{self.room_number} - {self.room_type.name} - {self.hotel.name}"
    
    class Meta:
        verbose_name_plural = "Rooms"

    def save(self, *args, **kwargs):
        # Keep hotel aligned with selected room type so admin filters and searches stay consistent.
        if self.room_type_id and (not self.hotel_id or self.hotel_id != self.room_type.hotel_id):
            self.hotel = self.room_type.hotel

        if self.room_type_id and (self.price is None or self.price == Decimal('0.00')):
            self.price = self.room_type.price

        # Keep the legacy and new availability flags aligned.
        if self.availability != self.is_available:
            self.is_available = self.availability

        super().save(*args, **kwargs)

    def room_price(self):
        if self.price is not None:
            return self.price
        return self.room_type.price
    
    def no_of_beds(self):
        return self.room_type.no_of_beds
    
class Booking(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings", null=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    Phone = models.CharField(max_length=20)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=(('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')), default='pending')
    total_days = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    booking_id = ShortUUIDField(length=8, unique=True, blank=True)

    def __str__(self):
        customer_name = self.customer.username if self.customer else (self.full_name or self.email)
        return f"Booking by {customer_name} for {self.hotel.name} - Room {self.room.room_number}"
    
    def rooms(self):
        # Booking links to exactly one room via ForeignKey.
        return 1 if self.room_id else 0
    class Meta:
        verbose_name_plural = "Bookings"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return self.user.username


class ContactMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.subject or "No subject"}'


class Review(models.Model):
    STAR_CHOICES = (
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    )

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reviews_received', blank=True, null=True)
    rating = models.PositiveSmallIntegerField(choices=STAR_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('hotel', 'user')

    def save(self, *args, **kwargs):
        if self.hotel_id:
            self.agent = self.hotel.agent
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} - {self.hotel.name} ({self.rating}/5)'



