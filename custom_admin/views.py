import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils.dateformat import format as date_format
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from hotel.models import Booking, ContactMessage, Hotel, Review, Room, RoomType
from hotel.notifications import send_booking_notification_email
from userauths.models import Profile, User


ADMIN_MODELS = {
    'hotels': Hotel,
    'rooms': Room,
    'room-types': RoomType,
    'bookings': Booking,
    'users': User,
    'profiles': Profile,
    'messages': ContactMessage,
    'reviews': Review,
}


def _to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_decimal(value, default='0.00'):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _is_admin_user(user):
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def _forbidden_json():
    return JsonResponse({'detail': 'Forbidden'}, status=403)


def _serialize_datetime(value):
    if not value:
        return '-'
    return date_format(value, 'Y-m-d H:i')


def _related_text(instance, relation_name, attr_name='name', default='-'):
    related = getattr(instance, relation_name, None)
    if not related:
        return default
    value = getattr(related, attr_name, None)
    return value if value not in (None, '') else default


@login_required(login_url='userauths:login')
def admin_panel(request):
    if not _is_admin_user(request.user):
        return HttpResponse('Forbidden', status=403)

    panel_file = Path(settings.BASE_DIR) / 'static' / 'custom_admin' / 'index.html'
    if not panel_file.exists():
        return HttpResponse('Admin panel file not found.', status=404)

    html = panel_file.read_text(encoding='utf-8')
    return HttpResponse(html)


@login_required(login_url='userauths:login')
def admin_logout(request):
    logout(request)
    return redirect('userauths:login')


@login_required(login_url='userauths:login')
def admin_legacy_redirect(request, legacy_path):
    if not _is_admin_user(request.user):
        return HttpResponse('Forbidden', status=403)

    normalized = (legacy_path or '').strip('/').lower()
    tab = 'dashboard'

    if normalized.startswith('hotel/hotel'):
        tab = 'hotels'
    elif normalized.startswith('hotel/roomtype'):
        tab = 'room-types'
    elif normalized.startswith('hotel/room'):
        tab = 'rooms'
    elif normalized.startswith('hotel/booking'):
        tab = 'bookings'
    elif normalized.startswith('userauths/user'):
        tab = 'users'

    return redirect(f'/admin/?tab={tab}')


@login_required(login_url='userauths:login')
def api_dashboard(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    stats = {
        'hotels': Hotel.objects.count(),
        'rooms': Room.objects.count(),
        'room_types': RoomType.objects.count(),
        'bookings': Booking.objects.count(),
        'users': User.objects.count(),
        'profiles': Profile.objects.count(),
        'messages': ContactMessage.objects.count(),
        'reviews': Review.objects.count(),
    }

    recent_bookings = []
    for booking in Booking.objects.select_related('hotel', 'room', 'customer').order_by('-date')[:8]:
        recent_bookings.append({
            'id': booking.id,
            'booking_id': booking.booking_id,
            'customer': booking.customer.username if booking.customer else booking.full_name,
            'hotel': _related_text(booking, 'hotel'),
            'room': _related_text(booking, 'room', 'room_number'),
            'amount': str(booking.total_price),
            'payment_status': booking.payment_status,
            'date': _serialize_datetime(booking.date),
        })

    return JsonResponse({'stats': stats, 'recent_bookings': recent_bookings})


@login_required(login_url='userauths:login')
def api_hotels(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    rows = []
    for hotel in Hotel.objects.select_related('agent').order_by('-created_at')[:200]:
        rows.append({
            'id': hotel.id,
            'name': hotel.name,
            'location': hotel.location or '-',
            'status': hotel.status,
            'featured': hotel.featured,
            'agent': hotel.agent.username if hotel.agent else '-',
            'created_at': _serialize_datetime(hotel.created_at),
        })

    return JsonResponse({'rows': rows})


@login_required(login_url='userauths:login')
def api_rooms(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    rows = []
    for room in Room.objects.select_related('hotel', 'room_type').order_by('-date')[:250]:
        rows.append({
            'id': room.id,
            'room_number': room.room_number,
            'hotel': _related_text(room, 'hotel'),
            'room_type': _related_text(room, 'room_type'),
            'price': str(room.price),
            'availability': room.availability,
            'date': _serialize_datetime(room.date),
        })

    return JsonResponse({'rows': rows})


@login_required(login_url='userauths:login')
def api_room_types(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    rows = []
    for room_type in RoomType.objects.select_related('hotel').order_by('-date')[:250]:
        rows.append({
            'id': room_type.id,
            'name': room_type.name,
            'hotel': _related_text(room_type, 'hotel'),
            'price': str(room_type.price),
            'beds': room_type.no_of_beds,
            'date': _serialize_datetime(room_type.date),
        })

    return JsonResponse({'rows': rows})


@login_required(login_url='userauths:login')
def api_bookings(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    rows = []
    for booking in Booking.objects.select_related('hotel', 'room', 'customer').order_by('-date')[:300]:
        rows.append({
            'id': booking.id,
            'booking_id': booking.booking_id,
            'customer': booking.customer.username if booking.customer else booking.full_name,
            'hotel': _related_text(booking, 'hotel'),
            'room': _related_text(booking, 'room', 'room_number'),
            'total_price': str(booking.total_price),
            'payment_status': booking.payment_status,
            'is_active': booking.is_active,
            'check_in': str(booking.check_in),
            'check_out': str(booking.check_out),
            'date': _serialize_datetime(booking.date),
        })

    return JsonResponse({'rows': rows})


@login_required(login_url='userauths:login')
def api_users(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    profile_map = {
        profile.user_id: profile
        for profile in Profile.objects.exclude(identity_image='').select_related('user')
    }

    rows = []
    for user in User.objects.order_by('-date_joined')[:300]:
        profile = profile_map.get(user.id)
        identity_image_url = ''
        identity_type = '-'
        if profile:
            identity_type = profile.identity_type or '-'
            if profile.identity_image:
                try:
                    identity_image_url = profile.identity_image.url
                except Exception:
                    identity_image_url = ''

        rows.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'agent_approval_status': user.agent_approval_status,
            'identity_type': identity_type,
            'agent_document_url': identity_image_url,
            'date_joined': _serialize_datetime(user.date_joined),
        })

    return JsonResponse({'rows': rows})


@login_required(login_url='userauths:login')
def api_messages(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    rows = []
    for message in ContactMessage.objects.select_related('user').order_by('-created_at')[:300]:
        rows.append({
            'id': message.id,
            'name': message.name,
            'email': message.email,
            'subject': message.subject or '-',
            'message': message.message,
            'is_read': message.is_read,
            'user': message.user.username if message.user else '-',
            'created_at': _serialize_datetime(message.created_at),
        })

    return JsonResponse({'rows': rows})


@login_required(login_url='userauths:login')
def api_reviews(request):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    rows = []
    for review in Review.objects.select_related('user', 'hotel', 'agent').order_by('-created_at')[:300]:
        rows.append({
            'id': review.id,
            'hotel': _related_text(review, 'hotel'),
            'customer': _related_text(review, 'user', 'username'),
            'agent': review.agent.username if review.agent else '-',
            'rating': review.rating,
            'comment': review.comment or '-',
            'created_at': _serialize_datetime(review.created_at),
        })

    return JsonResponse({'rows': rows})


@login_required(login_url='userauths:login')
@csrf_exempt
@require_http_methods(['POST'])
def api_save_object(request, model_name):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    model = ADMIN_MODELS.get(model_name)
    if model is None:
        return JsonResponse({'detail': 'Invalid model'}, status=404)

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    obj_id = payload.get('id')
    fields = payload.get('fields') or {}
    creating = not obj_id

    instance = model() if creating else model.objects.filter(pk=obj_id).first()
    if not creating and not instance:
        return JsonResponse({'detail': 'Object not found'}, status=404)

    if model_name == 'hotels':
        if creating and not (fields.get('name') or '').strip():
            return JsonResponse({'detail': 'Name is required.'}, status=400)
        instance.name = (fields.get('name') or getattr(instance, 'name', '')).strip()
        instance.location = (fields.get('location') or '').strip()
        instance.status = (fields.get('status') or 'pending').strip() or 'pending'
        instance.featured = _to_bool(fields.get('featured', False))
        agent_id = fields.get('agent_id')
        if agent_id:
            instance.agent = User.objects.filter(pk=_to_int(agent_id), role='agent').first()
        instance.save()

    elif model_name == 'rooms':
        if creating:
            hotel_id = _to_int(fields.get('hotel_id'))
            room_type_id = _to_int(fields.get('room_type_id'))
            hotel = Hotel.objects.filter(pk=hotel_id).first()
            room_type = RoomType.objects.filter(pk=room_type_id).first()
            if not hotel or not room_type:
                return JsonResponse({'detail': 'Valid hotel_id and room_type_id are required.'}, status=400)
            if room_type.hotel_id != hotel.id:
                return JsonResponse({'detail': 'Selected room type does not belong to selected hotel.'}, status=400)
            instance.hotel = hotel
            instance.room_type = room_type

        instance.room_number = (fields.get('room_number') or getattr(instance, 'room_number', '')).strip()
        if not instance.room_number:
            return JsonResponse({'detail': 'room_number is required.'}, status=400)
        instance.price = _to_decimal(fields.get('price', getattr(instance, 'price', '0.00')))
        instance.availability = _to_bool(fields.get('availability', getattr(instance, 'availability', True)))
        instance.is_available = instance.availability
        instance.save()

    elif model_name == 'room-types':
        if creating:
            hotel_id = _to_int(fields.get('hotel_id'))
            hotel = Hotel.objects.filter(pk=hotel_id).first()
            if not hotel:
                return JsonResponse({'detail': 'Valid hotel_id is required.'}, status=400)
            instance.hotel = hotel
        instance.name = (fields.get('name') or getattr(instance, 'name', '')).strip()
        if not instance.name:
            return JsonResponse({'detail': 'name is required.'}, status=400)
        instance.price = _to_decimal(fields.get('price', getattr(instance, 'price', '0.00')))
        instance.no_of_beds = _to_int(fields.get('no_of_beds', getattr(instance, 'no_of_beds', 1)), 1)
        instance.save()

    elif model_name == 'bookings':
        old_status = getattr(instance, 'payment_status', None)
        if creating:
            hotel = Hotel.objects.filter(pk=_to_int(fields.get('hotel_id'))).first()
            room_type = RoomType.objects.filter(pk=_to_int(fields.get('room_type_id'))).first()
            room = Room.objects.filter(pk=_to_int(fields.get('room_id'))).first()
            if not hotel or not room_type or not room:
                return JsonResponse({'detail': 'Valid hotel_id, room_type_id, and room_id are required.'}, status=400)
            if room.hotel_id != hotel.id:
                return JsonResponse({'detail': 'Selected room does not belong to the selected hotel.'}, status=400)
            if room.room_type_id != room_type.id:
                return JsonResponse({'detail': 'Selected room does not match selected room type.'}, status=400)

            check_in_raw = (fields.get('check_in') or '').strip()
            check_out_raw = (fields.get('check_out') or '').strip()
            try:
                check_in_date = datetime.strptime(check_in_raw, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out_raw, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'detail': 'check_in and check_out must be valid dates (YYYY-MM-DD).'}, status=400)

            if check_out_date <= check_in_date:
                return JsonResponse({'detail': 'check_out must be after check_in.'}, status=400)

            instance.customer = User.objects.filter(pk=_to_int(fields.get('customer_id'))).first()
            instance.full_name = (fields.get('full_name') or '').strip()
            instance.email = (fields.get('email') or '').strip()
            instance.Phone = (fields.get('phone') or '').strip()
            if not instance.full_name or not instance.email or not instance.Phone:
                return JsonResponse({'detail': 'full_name, email, and phone are required.'}, status=400)

            total_days = (check_out_date - check_in_date).days
            calculated_total = room.price * Decimal(total_days)
            provided_total = _to_decimal(fields.get('total_price', calculated_total))

            instance.hotel = hotel
            instance.room_type = room_type
            instance.room = room
            instance.check_in = check_in_date
            instance.check_out = check_out_date
            instance.total_days = total_days
            instance.total_price = provided_total if provided_total > Decimal('0.00') else calculated_total
            instance.payment_status = (fields.get('payment_status') or 'pending').strip() or 'pending'
            instance.is_active = _to_bool(fields.get('is_active', True))
        else:
            instance.payment_status = (fields.get('payment_status') or instance.payment_status).strip() or instance.payment_status
            instance.total_price = _to_decimal(fields.get('total_price', instance.total_price))
            instance.is_active = _to_bool(fields.get('is_active', instance.is_active))

        instance.save()
        if creating:
            send_booking_notification_email(instance, 'booking_created')
        elif old_status != instance.payment_status:
            send_booking_notification_email(instance, 'payment_status_changed', previous_status=old_status)

    elif model_name == 'users':
        if creating:
            username = (fields.get('username') or '').strip()
            email = (fields.get('email') or '').strip()
            role = (fields.get('role') or 'customer').strip() or 'customer'
            if not username or not email:
                return JsonResponse({'detail': 'username and email are required.'}, status=400)
            password = (fields.get('password') or 'Admin@12345').strip()
            instance = User.objects.create_user(username=username, email=email, role=role, password=password)
        else:
            instance.email = (fields.get('email') or instance.email).strip()
            instance.role = (fields.get('role') or instance.role).strip() or instance.role
            instance.agent_approval_status = (fields.get('agent_approval_status') or instance.agent_approval_status).strip() or instance.agent_approval_status
            instance.save()

    elif model_name == 'messages':
        if creating:
            instance.name = (fields.get('name') or '').strip()
            instance.email = (fields.get('email') or '').strip()
            if not instance.name or not instance.email:
                return JsonResponse({'detail': 'name and email are required.'}, status=400)
        else:
            instance.name = (fields.get('name') or instance.name).strip()
            instance.email = (fields.get('email') or instance.email).strip()
        instance.subject = (fields.get('subject') or '').strip()
        instance.message = (fields.get('message') or getattr(instance, 'message', '')).strip()
        instance.is_read = _to_bool(fields.get('is_read', getattr(instance, 'is_read', False)))
        user_id = fields.get('user_id')
        if user_id:
            instance.user = User.objects.filter(pk=_to_int(user_id)).first()
        instance.save()

    elif model_name == 'reviews':
        if creating:
            hotel = Hotel.objects.filter(pk=_to_int(fields.get('hotel_id'))).first()
            user = User.objects.filter(pk=_to_int(fields.get('user_id'))).first()
            if not hotel or not user:
                return JsonResponse({'detail': 'Valid hotel_id and user_id are required.'}, status=400)
            instance.hotel = hotel
            instance.user = user
        instance.rating = _to_int(fields.get('rating', getattr(instance, 'rating', 5)), 5)
        if instance.rating < 1 or instance.rating > 5:
            instance.rating = 5
        instance.comment = (fields.get('comment') or '').strip()
        agent_id = fields.get('agent_id')
        if agent_id:
            instance.agent = User.objects.filter(pk=_to_int(agent_id), role='agent').first()
        instance.save()

    else:
        return JsonResponse({'detail': 'CRUD for this model is not enabled.'}, status=400)

    return JsonResponse({'ok': True, 'id': instance.pk})


@login_required(login_url='userauths:login')
@csrf_exempt
@require_http_methods(['POST'])
def api_update_agent_status(request, user_id):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    user = User.objects.filter(id=user_id, role='agent').first()
    if not user:
        return JsonResponse({'detail': 'Agent not found'}, status=404)

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON'}, status=400)

    status_value = payload.get('status')
    reason = (payload.get('reason') or '').strip()

    if status_value not in {'approved', 'pending', 'rejected'}:
        return JsonResponse({'detail': 'Invalid status'}, status=400)

    user.agent_approval_status = status_value
    user.agent_rejection_reason = reason if status_value == 'rejected' else ''
    user.save(update_fields=['agent_approval_status', 'agent_rejection_reason'])

    return JsonResponse({'ok': True})


@login_required(login_url='userauths:login')
@csrf_exempt
@require_http_methods(['POST'])
def api_delete_object(request, model_name, obj_id):
    if not _is_admin_user(request.user):
        return _forbidden_json()

    model = ADMIN_MODELS.get(model_name)
    if model is None:
        return JsonResponse({'detail': 'Invalid model'}, status=404)

    instance = model.objects.filter(pk=obj_id).first()
    if not instance:
        return JsonResponse({'detail': 'Object not found'}, status=404)

    instance.delete()
    return JsonResponse({'ok': True})
