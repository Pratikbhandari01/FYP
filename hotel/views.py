from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.db.models import Exists, OuterRef, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from .models import RoomType, Hotel, Booking, Payment, Room, ContactMessage, Review
from .forms import ContactForm, HotelSearchForm, HotelForm, RoomForm, RoomTypeForm, ReviewForm
from .notifications import send_booking_notification_email
from userauths.decorators import agent_required
from django.utils.decorators import method_decorator
from userauths.decorators import customer_required


def _agent_booking_block(request):
    """Block agents from customer booking actions and redirect safely."""
    if request.user.is_authenticated and request.user.role == 'agent':
        messages.error(request, "Agents are not allowed to book rooms. Please use the agent dashboard.")
        return redirect('userauths:agent_dashboard')
    return None

@login_required
def profile_view(request):
    profile = getattr(request.user, 'profile', None)
    user_bookings = Booking.objects.filter(customer=request.user)

    total_bookings = user_bookings.count()
    completed_bookings = user_bookings.filter(booking_status='paid').count()
    pending_bookings = user_bookings.filter(booking_status='pending').count()
    failed_bookings = user_bookings.filter(payment_status='failed').count()
    cancelled_bookings = user_bookings.filter(booking_status='cancelled').count()
    total_amount_spent = (
        user_bookings.filter(booking_status='paid').aggregate(total=Sum('total_price')).get('total')
        or Decimal('0.00')
    )
    recent_bookings = (
        user_bookings.select_related('hotel', 'room')
        .order_by('-date')[:5]
    )

    return render(request, 'hotel/profile.html', {
        'user': request.user,
        'profile': profile,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'pending_bookings': pending_bookings,
        'failed_bookings': failed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_amount_spent': total_amount_spent,
        'recent_bookings': recent_bookings,
    })


class HotelListView(ListView):
    model = Hotel
    template_name = 'hotel/hotel_list.html'
    context_object_name = 'hotels'
    paginate_by = 9

    def get_queryset(self):
        queryset = Hotel.objects.all().order_by('-created_at', '-date')
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(location__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = HotelSearchForm(self.request.GET or None)
        return context


def index(request):
    hotels = Hotel.objects.filter(status="live")
    context = {
        'Hotels': hotels,
        'hotels': hotels,
    }
    return render(request, 'hotel/index.html', context)


def rooms(request):
    hotels = Hotel.objects.all().order_by('name')
    selected_hotel_id = request.GET.get('hotel')
    rooms_qs = Room.objects.select_related('hotel', 'room_type').filter(availability=True)

    if selected_hotel_id:
        rooms_qs = rooms_qs.filter(hotel_id=selected_hotel_id)

    context = {
        'hotels': hotels,
        'rooms': rooms_qs,
        'selected_hotel_id': selected_hotel_id,
    }
    return render(request, 'hotel/room_list.html', context)


def rooms_by_hotel_ajax(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    rooms_qs = (
        Room.objects.select_related('room_type')
        .filter(hotel=hotel, availability=True)
        .order_by('room_number')
    )
    data = [
        {
            'id': room.id,
            'hotel_id': room.hotel_id,
            'room_number': room.room_number,
            'price': str(room.price),
            'availability': room.availability,
            'room_type': room.room_type.name,
        }
        for room in rooms_qs
    ]
    return JsonResponse({'rooms': data})


def hotel_detail(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    rooms_qs = Room.objects.select_related('room_type').filter(hotel=hotel, availability=True).order_by('room_number')
    reviews = Review.objects.select_related('user').filter(hotel=hotel)

    review_form = None
    existing_review = None
    if request.user.is_authenticated and request.user.role == 'customer':
        existing_review = Review.objects.filter(hotel=hotel, user=request.user).first()
        review_form = ReviewForm(instance=existing_review)

    return render(request, 'hotel/hotel_detail.html', {
        'hotel': hotel,
        'rooms': rooms_qs,
        'reviews': reviews,
        'review_form': review_form,
        'existing_review': existing_review,
    })


@login_required
@customer_required
def add_review(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)

    if request.method != 'POST':
        return redirect('hotel:hotel_detail', hotel_id=hotel.id)

    existing_review = Review.objects.filter(hotel=hotel, user=request.user).first()
    form = ReviewForm(request.POST, instance=existing_review)
    if form.is_valid():
        review = form.save(commit=False)
        review.hotel = hotel
        review.user = request.user
        review.agent = hotel.agent
        review.save()
        if existing_review:
            messages.success(request, 'Your review has been updated.')
        else:
            messages.success(request, 'Thanks! Your review has been posted.')
    else:
        messages.error(request, 'Please provide a valid rating and comment.')

    return redirect('hotel:hotel_detail', hotel_id=hotel.id)


@login_required
@customer_required
def delete_review(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)

    if request.method != 'POST':
        return redirect('hotel:hotel_detail', hotel_id=hotel.id)

    review = Review.objects.filter(hotel=hotel, user=request.user).first()
    if not review:
        messages.error(request, 'You do not have a review to delete for this hotel.')
        return redirect('hotel:hotel_detail', hotel_id=hotel.id)

    review.delete()
    messages.success(request, 'Your review has been deleted.')
    return redirect('hotel:hotel_detail', hotel_id=hotel.id)


def _khalti_headers():
    secret_key = settings.KHALTI_SECRET_KEY.strip().strip('"').strip("'")
    if secret_key.lower().startswith('key '):
        secret_key = secret_key[4:].strip()

    return {
        'Authorization': f'Key {secret_key}',
        'Content-Type': 'application/json',
    }


def _extract_khalti_error(payload):
    if not isinstance(payload, dict):
        return 'Unexpected response from Khalti.'

    detail = payload.get('detail')
    if isinstance(detail, str) and detail.strip():
        return detail.strip()

    error_key = payload.get('error_key')
    if isinstance(error_key, str) and error_key.strip():
        return error_key.strip()

    if detail and isinstance(detail, list):
        joined = '; '.join(str(item) for item in detail if str(item).strip())
        if joined:
            return joined

    return 'Payment request rejected by Khalti.'


def _is_invalid_token_error(payload):
    reason = _extract_khalti_error(payload).lower()
    return 'invalid token' in reason or 'unauthorized' in reason


def _initiate_khalti_payment(request, booking):
    if not settings.KHALTI_SECRET_KEY:
        messages.error(request, 'Khalti secret key is not configured on server. Set KHALTI_SECRET_KEY first.')
        return redirect('hotel:customer_bookings')

    return_url = request.build_absolute_uri(reverse('hotel:khalti_payment_callback'))
    website_url = request.build_absolute_uri('/')
    amount_paisa = int(booking.total_price * Decimal('100'))

    payload = {
        'return_url': return_url,
        'website_url': website_url,
        'amount': amount_paisa,
        'purchase_order_id': booking.booking_id,
        'purchase_order_name': f'Room {booking.room.room_number} at {booking.hotel.name}',
        'customer_info': {
            'name': booking.full_name,
            'email': booking.email,
            'phone': booking.Phone,
        },
    }

    try:
        response = requests.post(
            settings.KHALTI_INITIATE_URL,
            json=payload,
            headers=_khalti_headers(),
            timeout=20,
        )
        data = response.json()
    except (requests.RequestException, ValueError):
        messages.error(request, 'Could not reach Khalti. Your booking is saved as pending. Please try payment again.')
        return redirect('hotel:customer_bookings')

    if response.status_code != 200 and _is_invalid_token_error(data):
        try:
            sandbox_response = requests.post(
                'https://dev.khalti.com/api/v2/epayment/initiate/',
                json=payload,
                headers=_khalti_headers(),
                timeout=20,
            )
            sandbox_data = sandbox_response.json()
        except (requests.RequestException, ValueError):
            sandbox_response = None
            sandbox_data = None

        if sandbox_response is not None and sandbox_response.status_code == 200 and sandbox_data.get('payment_url'):
            Payment.objects.create(
                booking=booking,
                payment_method='khalti',
                amount=booking.total_price,
                payment_status='pending',
                transaction_id=(sandbox_data.get('pidx') or ''),
            )
            return redirect(sandbox_data['payment_url'])

    payment_url = data.get('payment_url')
    if response.status_code != 200 or not payment_url:
        khalti_reason = _extract_khalti_error(data)
        if _is_invalid_token_error(data):
            khalti_reason = (
                f'{khalti_reason} Use sandbox keys with dev endpoint or live keys with live endpoint. '
                'Also make sure KHALTI_SECRET_KEY does not include the text "Key".'
            )
        messages.error(request, f'Khalti payment could not be initialized. Booking is pending: {khalti_reason}')
        return redirect('hotel:customer_bookings')

    Payment.objects.create(
        booking=booking,
        payment_method='khalti',
        amount=booking.total_price,
        payment_status='pending',
        transaction_id=(data.get('pidx') or ''),
    )
    return redirect(payment_url)


@login_required(login_url='userauths:login')
def book_room(request, room_id):
    blocked_response = _agent_booking_block(request)
    if blocked_response is not None:
        return blocked_response

    try:
        room = Room.objects.select_related('hotel', 'room_type').get(pk=room_id)
    except Room.DoesNotExist:
        messages.error(request, "Requested room does not exist.")
        return redirect('hotel:rooms')

    if not room.availability:
        messages.warning(request, "This room is already booked.")
        return redirect('hotel:rooms')

    today = datetime.now().date()
    book_context = {
        'room': room,
        'today': today,
        'form_values': {
            'full_name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'phone': getattr(request.user, 'phone', ''),
            'check_in': '',
            'check_out': '',
            'guests': '1',
        },
    }

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip() or request.user.username
        email = request.POST.get('email', '').strip() or request.user.email
        phone = request.POST.get('phone', '').strip()
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        guests_raw = request.POST.get('guests', '1').strip()

        book_context['form_values'] = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'check_in': check_in or '',
            'check_out': check_out or '',
            'guests': guests_raw or '1',
        }

        if not phone or not check_in or not check_out or not guests_raw:
            messages.error(request, "Please fill out all booking fields.")
            return render(request, 'hotel/book_room.html', book_context)

        try:
            guests = int(guests_raw)
        except (TypeError, ValueError):
            messages.error(request, 'Please enter a valid number of guests.')
            return render(request, 'hotel/book_room.html', book_context)

        if guests < 1 or guests > 10:
            messages.error(request, 'Guests must be between 1 and 10.')
            return render(request, 'hotel/book_room.html', book_context)

        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return render(request, 'hotel/book_room.html', book_context)

        if check_in_date < today:
            messages.error(request, "Check-in date cannot be in the past.")
            return render(request, 'hotel/book_room.html', book_context)

        if check_out_date < today:
            messages.error(request, "Check-out date cannot be in the past.")
            return render(request, 'hotel/book_room.html', book_context)

        if check_out_date <= check_in_date:
            messages.error(request, "Check-out date must be after check-in date.")
            return render(request, 'hotel/book_room.html', book_context)

        if not room.availability or not room.is_available:
            messages.error(request, 'This room is no longer available.')
            return redirect('hotel:rooms')

        total_days = (check_out_date - check_in_date).days
        total_price = room.price * Decimal(total_days)

        booking = Booking.objects.create(
            customer=request.user,
            full_name=full_name,
            email=email,
            Phone=phone,
            hotel=room.hotel,
            room_type=room.room_type,
            room=room,
            check_in=check_in_date,
            check_out=check_out_date,
            guests=guests,
            total_price=total_price,
            total_days=total_days,
            booking_status='pending',
            payment_status='pending',
        )

        send_booking_notification_email(booking, 'booking_created')
        messages.success(request, 'Booking created. Complete payment to confirm your stay.')
        return _initiate_khalti_payment(request, booking)

    return render(request, 'hotel/book_room.html', book_context)


@login_required(login_url='userauths:login')
@customer_required
def proceed_booking_payment(request, booking_id):
    blocked_response = _agent_booking_block(request)
    if blocked_response is not None:
        return blocked_response

    booking = get_object_or_404(
        Booking.objects.select_related('hotel', 'room'),
        booking_id=booking_id,
        customer=request.user,
    )

    if booking.booking_status == 'cancelled':
        messages.error(request, 'This booking has been cancelled and cannot be paid.')
        return redirect('hotel:customer_bookings')

    if booking.booking_status == 'paid' or booking.payment_status == 'completed':
        messages.info(request, 'This booking is already paid.')
        return redirect('hotel:customer_bookings')

    if not booking.room.availability or not booking.room.is_available:
        messages.error(request, 'This room is unavailable. Please choose another room.')
        return redirect('hotel:rooms')

    return _initiate_khalti_payment(request, booking)


@login_required(login_url='userauths:login')
@customer_required
def cancel_booking(request, booking_id):
    if request.method != 'POST':
        return redirect('hotel:customer_bookings')

    booking = get_object_or_404(Booking, booking_id=booking_id, customer=request.user)

    if booking.booking_status == 'paid' or booking.payment_status == 'completed':
        messages.error(request, 'Paid bookings cannot be cancelled from this page. Please contact support.')
        return redirect('hotel:customer_bookings')

    if booking.booking_status == 'cancelled':
        messages.info(request, 'This booking is already cancelled.')
        return redirect('hotel:customer_bookings')

    booking.booking_status = 'cancelled'
    booking.payment_status = 'cancelled'
    booking.is_active = False
    booking.save(update_fields=['booking_status', 'payment_status', 'is_active'])

    Payment.objects.create(
        booking=booking,
        payment_method='khalti',
        amount=booking.total_price,
        payment_status='cancelled',
    )
    send_booking_notification_email(booking, 'booking_cancelled')
    messages.success(request, f'Booking {booking.booking_id} has been cancelled.')
    return redirect('hotel:customer_bookings')


@login_required(login_url='userauths:login')
def khalti_payment_callback(request):
    blocked_response = _agent_booking_block(request)
    if blocked_response is not None:
        return blocked_response

    pidx = request.GET.get('pidx')
    booking_id = request.GET.get('purchase_order_id')

    if not pidx or not booking_id:
        messages.error(request, 'Payment verification failed due to missing Khalti data.')
        return redirect('hotel:rooms')

    booking = get_object_or_404(Booking, booking_id=booking_id, customer=request.user)

    if booking.booking_status == 'cancelled':
        messages.error(request, 'This booking was cancelled and cannot be paid.')
        return redirect('hotel:customer_bookings')

    try:
        lookup_response = requests.post(
            settings.KHALTI_LOOKUP_URL,
            json={'pidx': pidx},
            headers=_khalti_headers(),
            timeout=20,
        )
        lookup_data = lookup_response.json()
    except (requests.RequestException, ValueError):
        messages.error(request, 'Could not verify Khalti payment. Please contact support if amount was deducted.')
        return redirect('hotel:customer_bookings')

    if lookup_response.status_code == 200 and lookup_data.get('status') == 'Completed':
        previous_status = booking.payment_status
        booking.payment_status = 'completed'
        booking.booking_status = 'paid'
        booking.save(update_fields=['payment_status', 'booking_status'])
        if previous_status != 'completed':
            send_booking_notification_email(booking, 'payment_completed', previous_status=previous_status)

        pending_payment = (
            Payment.objects.filter(booking=booking, payment_status='pending')
            .order_by('-created_at')
            .first()
        )
        if pending_payment:
            pending_payment.payment_status = 'paid'
            pending_payment.transaction_id = pending_payment.transaction_id or pidx
            pending_payment.paid_at = timezone.now()
            pending_payment.save(update_fields=['payment_status', 'transaction_id', 'paid_at'])
        else:
            Payment.objects.create(
                booking=booking,
                payment_method='khalti',
                amount=booking.total_price,
                payment_status='paid',
                transaction_id=pidx,
                paid_at=timezone.now(),
            )

        if booking.room.availability or booking.room.is_available:
            booking.room.availability = False
            booking.room.is_available = False
            booking.room.save(update_fields=['availability', 'is_available'])

        messages.success(request, f'Payment successful. Room {booking.room.room_number} is now booked.')
        return redirect('hotel:customer_bookings')

    previous_status = booking.payment_status
    booking.payment_status = 'pending'
    booking.booking_status = 'pending'
    booking.save(update_fields=['payment_status', 'booking_status'])

    Payment.objects.create(
        booking=booking,
        payment_method='khalti',
        amount=booking.total_price,
        payment_status='failed',
        transaction_id=pidx,
    )

    send_booking_notification_email(booking, 'payment_failed', previous_status=previous_status)
    fail_reason = _extract_khalti_error(lookup_data)
    messages.warning(request, f'Payment was not completed. Booking is still pending: {fail_reason}')
    return redirect('hotel:customer_bookings')


def about(request):
    return render(request, 'hotel/about.html')


def contact(request):
    """Render the Contact Us page and handle contact form submissions."""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            ContactMessage.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject=form.cleaned_data['subject'],
                message=form.cleaned_data['message'],
            )
            messages.success(request, "Thanks for reaching out! We'll get back to you soon.")
            return redirect('hotel:contact')
    else:
        form = ContactForm()

    return render(request, 'hotel/contact.html', {'form': form})


def room_types_api(request):
    """API endpoint to get room types filtered by hotel."""
    hotel_id = request.GET.get('hotel_id')
    
    if not hotel_id:
        return JsonResponse({'error': 'hotel_id is required'}, status=400)
    
    try:
        hotel_id = int(hotel_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid hotel_id'}, status=400)
    
    room_types = RoomType.objects.filter(hotel_id=hotel_id).values('id', 'name', 'price', 'hotel_id').order_by('name')
    
    return JsonResponse(list(room_types), safe=False)

@method_decorator(login_required, name='dispatch')
@method_decorator(agent_required, name='dispatch')
class AgentHotelListView(ListView):
    model = Hotel
    template_name = 'hotel/agent_hotel_list.html'
    context_object_name = 'hotels'

    def get_queryset(self):
        return Hotel.objects.filter(agent=self.request.user)

@method_decorator(login_required, name='dispatch')
@method_decorator(agent_required, name='dispatch')
class CreateHotelView(CreateView):
    model = Hotel
    form_class = HotelForm
    template_name = 'hotel/create_hotel.html'
    success_url = reverse_lazy('hotel:agent_hotel_list')

    def form_valid(self, form):
        form.instance.agent = self.request.user
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
@method_decorator(agent_required, name='dispatch')
class UpdateHotelView(UpdateView):
    model = Hotel
    form_class = HotelForm
    template_name = 'hotel/update_hotel.html'
    success_url = reverse_lazy('hotel:agent_hotel_list')

    def get_queryset(self):
        return Hotel.objects.filter(agent=self.request.user)

@method_decorator(login_required, name='dispatch')
@method_decorator(agent_required, name='dispatch')
class DeleteHotelView(DeleteView):
    model = Hotel
    template_name = 'hotel/delete_hotel.html'
    success_url = reverse_lazy('hotel:agent_hotel_list')

    def get_queryset(self):
        return Hotel.objects.filter(agent=self.request.user)

@login_required
@customer_required
def customer_bookings(request):
    completed_match = Booking.objects.filter(
        customer_id=request.user.id,
        room_id=OuterRef('room_id'),
        check_in=OuterRef('check_in'),
        check_out=OuterRef('check_out'),
        payment_status='completed',
    )

    bookings = (
        Booking.objects.select_related('hotel', 'room')
        .filter(customer_id=request.user.id)
        .annotate(has_completed_match=Exists(completed_match))
        .exclude(payment_status='pending', has_completed_match=True)
        .order_by('-date')
    )
    return render(request, 'hotel/customer_bookings.html', {'bookings': bookings})


@login_required
@agent_required
def agent_bookings(request):
    bookings = (
        Booking.objects.select_related('hotel', 'room', 'customer')
        .filter(hotel__agent=request.user)
        .order_by('-date')
    )
    return render(request, 'hotel/agent_bookings.html', {'bookings': bookings})


@login_required
@agent_required
def add_room(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, agent=request.user)
    room_type_queryset = RoomType.objects.filter(hotel=hotel)

    if request.method == 'POST':
        form = RoomForm(request.POST)
        form.fields['room_type'].queryset = room_type_queryset
        if form.is_valid():
            room = form.save(commit=False)
            room.hotel = hotel
            room.save()
            messages.success(request, f"Room {room.room_number} has been added to {hotel.name}.")
            return redirect('hotel:agent_hotel_list')
    else:
        form = RoomForm()
        form.fields['room_type'].queryset = room_type_queryset

    context = {
        'form': form,
        'hotel': hotel,
        'room_type_count': room_type_queryset.count(),
    }
    return render(request, 'hotel/add_room.html', context)


@login_required
@agent_required
def room_type_list(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, agent=request.user)
    room_types = RoomType.objects.filter(hotel=hotel).order_by('name')
    return render(request, 'hotel/room_type_list.html', {'hotel': hotel, 'room_types': room_types})


@login_required
@agent_required
def add_room_type(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, agent=request.user)

    if request.method == 'POST':
        form = RoomTypeForm(request.POST, request.FILES)
        if form.is_valid():
            room_type = form.save(commit=False)
            room_type.hotel = hotel
            room_type.save()
            messages.success(request, f"Room type '{room_type.name}' added for {hotel.name}.")
            return redirect('hotel:room_type_list', hotel_id=hotel.id)
    else:
        form = RoomTypeForm()

    return render(request, 'hotel/create_room_type.html', {'form': form, 'hotel': hotel})


@login_required
@agent_required
def update_room_type(request, hotel_id, room_type_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, agent=request.user)
    room_type = get_object_or_404(RoomType, id=room_type_id, hotel=hotel)

    if request.method == 'POST':
        form = RoomTypeForm(request.POST, request.FILES, instance=room_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Room type '{room_type.name}' updated.")
            return redirect('hotel:room_type_list', hotel_id=hotel.id)
    else:
        form = RoomTypeForm(instance=room_type)

    context = {'form': form, 'hotel': hotel, 'room_type': room_type}
    return render(request, 'hotel/update_room_type.html', context)


@login_required
@agent_required
def delete_room_type(request, hotel_id, room_type_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, agent=request.user)
    room_type = get_object_or_404(RoomType, id=room_type_id, hotel=hotel)

    if request.method == 'POST':
        deleted_name = room_type.name
        room_type.delete()
        messages.success(request, f"Room type '{deleted_name}' deleted.")
        return redirect('hotel:room_type_list', hotel_id=hotel.id)

    return render(request, 'hotel/delete_room_type.html', {'hotel': hotel, 'room_type': room_type})