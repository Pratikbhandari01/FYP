(function() {
    document.addEventListener('DOMContentLoaded', function() {
        // Handle room_type filtering based on hotel selection
        const hotelField = document.getElementById('id_hotel');
        const roomTypeField = document.getElementById('id_room_type');
        
        if (!hotelField || !roomTypeField) return;
        
        function updateRoomTypeOptions() {
            const selectedHotelId = hotelField.value;
            
            if (!selectedHotelId) {
                roomTypeField.innerHTML = '<option value="">---------</option>';
                return;
            }
            
            // Clear current options
            roomTypeField.innerHTML = '<option value="">---------</option>';
            
            // Fetch available room types for this hotel via AJAX
            const xhr = new XMLHttpRequest();
            xhr.open('GET', `/api/room-types/?hotel_id=${selectedHotelId}`, true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            
            xhr.onload = function() {
                if (xhr.status === 200) {
                    try {
                        const roomTypes = JSON.parse(xhr.responseText);
                        roomTypes.forEach(rt => {
                            const option = document.createElement('option');
                            option.value = rt.id;
                            option.text = rt.name + ' (₹' + rt.price + ')';
                            option.dataset.hotelId = rt.hotel_id;
                            roomTypeField.appendChild(option);
                        });
                    } catch (e) {
                        console.error('Error parsing room types:', e);
                    }
                }
            };
            
            xhr.onerror = function() {
                console.error('Error loading room types');
            };
            
            xhr.send();
        }
        
        // Listen for hotel field changes
        hotelField.addEventListener('change', updateRoomTypeOptions);
    });
})();
