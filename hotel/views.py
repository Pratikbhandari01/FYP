from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import RoomType, Hotel, Booking, Room, ContactMessage
from .forms import ContactForm, HotelSearchForm, HotelForm, RoomForm, RoomTypeForm
from userauths.decorators import agent_required
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from userauths.decorators import customer_required

@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, 'hotel/profile.html', {
        'user': request.user,
        'profile': profile
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
    return render(request, 'hotel/hotel_detail.html', {
        'hotel': hotel,
        'rooms': rooms_qs,
    })


@login_required(login_url='userauths:login')
def book_room(request, room_id):
    try:
        room = Room.objects.select_related('hotel', 'room_type').get(pk=room_id)
    except Room.DoesNotExist:
        messages.error(request, "Requested room does not exist.")
        return redirect('hotel:rooms')

    if not room.availability:
        messages.warning(request, "This room is already booked.")
        return redirect('hotel:rooms')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip() or request.user.username
        email = request.POST.get('email', '').strip() or request.user.email
        phone = request.POST.get('phone', '').strip()
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')

        if not phone or not check_in or not check_out:
            messages.error(request, "Please fill out all booking fields.")
            return render(request, 'hotel/book_room.html', {'room': room})

        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
            return render(request, 'hotel/book_room.html', {'room': room})

        if check_out_date <= check_in_date:
            messages.error(request, "Check-out date must be after check-in date.")
            return render(request, 'hotel/book_room.html', {'room': room})

        total_days = (check_out_date - check_in_date).days
        total_price = room.price * Decimal(total_days)

        Booking.objects.create(
            user=request.user,
            full_name=full_name,
            email=email,
            Phone=phone,
            hotel=room.hotel,
            room_type=room.room_type,
            room=room,
            check_in=check_in_date,
            check_out=check_out_date,
            total_price=total_price,
            total_days=total_days,
            payment_status='pending',
        )

        room.availability = False
        room.is_available = False
        room.save()

        messages.success(request, f"Booking successful! Your room {room.room_number} is reserved.")
        return redirect('hotel:rooms')

    return render(request, 'hotel/book_room.html', {'room': room})


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
    bookings = Booking.objects.filter(customer=request.user)
    return render(request, 'hotel/customer_bookings.html', {'bookings': bookings})


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