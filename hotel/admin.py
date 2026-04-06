from django.contrib import admin
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from .models import Booking, ContactMessage, Hotel, RoomType, Room






class RoomAdminForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get hotel_id from instance first (for editing existing rooms)
        hotel_id = None
        if self.instance and self.instance.pk and self.instance.hotel_id:
            hotel_id = self.instance.hotel_id
        
        # Then check POST/GET data (for form submission)
        if self.data and 'hotel' in self.data:
            try:
                hotel_id = int(self.data.get('hotel'))
            except (ValueError, TypeError):
                pass
        
        # Filter room_type queryset based on hotel
        if hotel_id:
            room_type_qs = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
            self.fields['room_type'].queryset = room_type_qs
            self.fields['room_type'].help_text = 'Available room types for selected hotel'
        else:
            # Show all room types if no hotel selected yet
            self.fields['room_type'].queryset = RoomType.objects.all().order_by('name')
            self.fields['room_type'].help_text = 'Select a hotel first to see available room types'

    def clean(self):
        cleaned_data = super().clean()
        hotel = cleaned_data.get('hotel')
        room_type = cleaned_data.get('room_type')

        if hotel and room_type and room_type.hotel_id != hotel.id:
            raise forms.ValidationError(
                'Selected room type does not belong to the selected hotel. Please choose a room type from the same hotel.'
            )

        # Auto-assign hotel from room_type if not set
        if room_type and not hotel:
            cleaned_data['hotel'] = room_type.hotel

        return cleaned_data


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ('room_type', 'room_number', 'price', 'availability', 'is_available', 'date')
    readonly_fields = ('date',)
    show_change_link = True
    form = RoomAdminForm

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # If this is a specific hotel, filter room_type options on the inline form class
        if obj:
            room_type_qs = RoomType.objects.filter(hotel=obj)
            formset.form.base_fields['room_type'].queryset = room_type_qs
        return formset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'room_type':
            object_id = request.resolver_match.kwargs.get('object_id')
            if object_id:
                kwargs['queryset'] = RoomType.objects.filter(hotel_id=object_id)
            else:
                kwargs['queryset'] = RoomType.objects.none()
        elif db_field.name == 'hotel':
            # Always restrict hotel to the parent hotel
            object_id = request.resolver_match.kwargs.get('object_id')
            if object_id:
                kwargs['queryset'] = Hotel.objects.filter(id=object_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'name', 'location', 'status', 'featured', 'created_at', 'manage_actions']
    list_filter = ['status', 'featured']
    search_fields = ['name', 'location', 'email']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [RoomInline]
    list_editable = ['status', 'featured']
    list_per_page = 20
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'location', 'address', 'mobile', 'email', 'description', 'image', 'status', 'featured', 'slug', 'created_at')
        }),
    )

    def manage_actions(self, obj):
        change_url = reverse('admin:hotel_hotel_change', args=[obj.pk])
        delete_url = reverse('admin:hotel_hotel_delete', args=[obj.pk])
        return format_html(
            '<a class="crud-btn crud-btn-edit" href="{}">Edit</a> '
            '<a class="crud-btn crud-btn-delete" href="{}">Delete</a>',
            change_url,
            delete_url,
        )
    manage_actions.short_description = 'Actions'


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    form = RoomAdminForm
    list_display = ['room_number', 'hotel', 'room_type', 'price', 'availability', 'date', 'manage_actions']
    list_filter = ['hotel', 'room_type', 'availability']
    search_fields = ['room_number', 'hotel__name', 'hotel__location', 'hotel__address', 'room_type__name']
    list_editable = ['price', 'availability']
    list_per_page = 25
    ordering = ['-date']
    autocomplete_fields = ['hotel']
    actions = ['mark_available', 'mark_unavailable']
    
    class Media:
        js = ('admin/js/room_admin.js',)

    def save_model(self, request, obj, form, change):
        if obj.room_type_id and obj.hotel_id != obj.room_type.hotel_id:
            obj.hotel = obj.room_type.hotel
        obj.is_available = obj.availability
        super().save_model(request, obj, form, change)

    def manage_actions(self, obj):
        change_url = reverse('admin:hotel_room_change', args=[obj.pk])
        delete_url = reverse('admin:hotel_room_delete', args=[obj.pk])
        return format_html(
            '<a class="crud-btn crud-btn-edit" href="{}">Edit</a> '
            '<a class="crud-btn crud-btn-delete" href="{}">Delete</a>',
            change_url,
            delete_url,
        )
    manage_actions.short_description = 'Actions'

    def mark_available(self, request, queryset):
        queryset.update(is_available=True, availability=True)
        self.message_user(request, "Selected rooms are now available.")
    mark_available.short_description = "Mark selected rooms as available"

    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False, availability=False)
        self.message_user(request, "Selected rooms are now unavailable.")
    mark_unavailable.short_description = "Mark selected rooms as unavailable"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'customer', 'hotel', 'room', 'check_in', 'check_out', 'total_price', 'payment_status', 'is_active', 'manage_actions']
    list_filter = ['payment_status', 'is_active', 'check_in', 'check_out']
    search_fields = ['booking_id', 'customer__username', 'hotel__name', 'room__room_number']
    readonly_fields = ['booking_id', 'date']
    list_per_page = 25
    ordering = ['-date']
    fieldsets = (
        (None, {
            'fields': ('customer', 'full_name', 'email', 'Phone', 'hotel', 'room_type', 'room', 'check_in', 'check_out', 'total_price', 'total_days', 'payment_status', 'is_active', 'booking_id')
        }),
    )
    actions = ['mark_completed', 'mark_pending', 'mark_failed']

    def mark_completed(self, request, queryset):
        queryset.update(payment_status='completed')
        self.message_user(request, "Selected bookings are marked completed.")
    mark_completed.short_description = "Mark selected bookings as completed"

    def mark_pending(self, request, queryset):
        queryset.update(payment_status='pending')
        self.message_user(request, "Selected bookings are marked pending.")
    mark_pending.short_description = "Mark selected bookings as pending"

    def mark_failed(self, request, queryset):
        queryset.update(payment_status='failed')
        self.message_user(request, "Selected bookings are marked failed.")
    mark_failed.short_description = "Mark selected bookings as failed"

    def manage_actions(self, obj):
        change_url = reverse('admin:hotel_booking_change', args=[obj.pk])
        delete_url = reverse('admin:hotel_booking_delete', args=[obj.pk])
        return format_html(
            '<a class="crud-btn crud-btn-edit" href="{}">Edit</a> '
            '<a class="crud-btn crud-btn-delete" href="{}">Delete</a>',
            change_url,
            delete_url,
        )
    manage_actions.short_description = 'Actions'


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'hotel', 'price', 'no_of_beds', 'date', 'manage_actions']
    list_filter = ['hotel', 'no_of_beds']
    search_fields = ['name', 'hotel__name']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25
    ordering = ['-date']
    autocomplete_fields = ['hotel']

    def manage_actions(self, obj):
        change_url = reverse('admin:hotel_roomtype_change', args=[obj.pk])
        delete_url = reverse('admin:hotel_roomtype_delete', args=[obj.pk])
        return format_html(
            '<a class="crud-btn crud-btn-edit" href="{}">Edit</a> '
            '<a class="crud-btn crud-btn-delete" href="{}">Delete</a>',
            change_url,
            delete_url,
        )
    manage_actions.short_description = 'Actions'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    list_editable = ['is_read']




# Apply basic theme labels for admin header/footer
admin.site.site_header = 'Nepstay.com'
admin.site.site_title = 'Nepstay.com Admin'
admin.site.index_title = 'Nepstay.com Dashboard'
