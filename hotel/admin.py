from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Booking, Hotel, RoomType, Room


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ('room_type', 'room_number', 'price', 'availability', 'is_available', 'date')
    readonly_fields = ('date',)
    show_change_link = True


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
    list_display = ['room_number', 'hotel', 'room_type', 'price', 'availability', 'date', 'manage_actions']
    list_filter = ['hotel', 'room_type', 'availability']
    search_fields = ['room_number', 'hotel__name', 'room_type__name']
    list_editable = ['price', 'availability']
    list_per_page = 25
    ordering = ['-date']
    autocomplete_fields = ['hotel', 'room_type']
    actions = ['mark_available', 'mark_unavailable']

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
    list_display = ['booking_id', 'user', 'hotel', 'room', 'check_in', 'check_out', 'total_price', 'payment_status', 'is_active', 'manage_actions']
    list_filter = ['payment_status', 'is_active', 'check_in', 'check_out']
    search_fields = ['booking_id', 'user__username', 'hotel__name', 'room__room_number']
    readonly_fields = ['booking_id', 'date']
    list_per_page = 25
    ordering = ['-date']
    fieldsets = (
        (None, {
            'fields': ('user', 'full_name', 'email', 'Phone', 'hotel', 'room_type', 'room', 'check_in', 'check_out', 'total_price', 'total_days', 'payment_status', 'is_active', 'booking_id')
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




# Apply basic theme labels for admin header/footer
admin.site.site_header = 'Nepstay.com'
admin.site.site_title = 'Nepstay.com Admin'
admin.site.index_title = 'Nepstay.com Dashboard'
