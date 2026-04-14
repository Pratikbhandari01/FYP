from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
import logging


logger = logging.getLogger(__name__)


def _is_valid_email(value):
    if not value:
        return False
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False


def send_booking_notification_email(booking, event, previous_status=None):
    """Send booking/payment notification email when recipient email is valid."""
    recipient = (booking.email or '').strip()
    if not _is_valid_email(recipient):
        return False

    hotel_name = booking.hotel.name if booking.hotel_id else 'your hotel'
    room_number = booking.room.room_number if booking.room_id else '-'

    event_key = (event or '').strip().lower()

    if event_key == 'booking_created':
        subject = f'Booking received: {booking.booking_id}'
        body = (
            f'Hi {booking.full_name},\n\n'
            f'We received your booking request for {hotel_name} (Room {room_number}).\n'
            f'Check-in: {booking.check_in}\n'
            f'Check-out: {booking.check_out}\n'
            f'Total amount: NPR {booking.total_price}\n'
            f'Payment status: {booking.payment_status.title()}\n\n'
            f'Thank you for choosing NepStay.'
        )
    elif event_key == 'payment_completed':
        subject = f'Payment successful: {booking.booking_id}'
        body = (
            f'Hi {booking.full_name},\n\n'
            f'Your payment is successful for booking {booking.booking_id}.\n'
            f'Hotel: {hotel_name}\n'
            f'Room: {room_number}\n'
            f'Amount paid: NPR {booking.total_price}\n\n'
            f'Your booking is confirmed. We look forward to hosting you.'
        )
    elif event_key == 'payment_failed':
        subject = f'Payment failed: {booking.booking_id}'
        body = (
            f'Hi {booking.full_name},\n\n'
            f'Your payment could not be completed for booking {booking.booking_id}.\n'
            f'Hotel: {hotel_name}\n'
            f'Room: {room_number}\n'
            f'Amount: NPR {booking.total_price}\n\n'
            f'Please try again or contact support if money was deducted.'
        )
    elif event_key == 'payment_status_changed':
        old = (previous_status or 'unknown').title()
        new = (booking.payment_status or 'unknown').title()
        subject = f'Booking payment update: {booking.booking_id}'
        body = (
            f'Hi {booking.full_name},\n\n'
            f'Your payment status changed for booking {booking.booking_id}.\n'
            f'Previous status: {old}\n'
            f'Current status: {new}\n'
            f'Hotel: {hotel_name}\n'
            f'Room: {room_number}\n\n'
            f'If you did not expect this update, please contact support.'
        )
    else:
        return False

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception(
            'Failed to send booking notification email for booking_id=%s event=%s',
            booking.booking_id,
            event_key,
        )
        return False
