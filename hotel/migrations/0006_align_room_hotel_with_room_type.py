from django.db import migrations


def align_room_hotel_with_room_type(apps, schema_editor):
    Room = apps.get_model('hotel', 'Room')

    for room in Room.objects.select_related('room_type').all():
        if room.room_type_id and room.hotel_id != room.room_type.hotel_id:
            room.hotel_id = room.room_type.hotel_id
            room.save(update_fields=['hotel'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0005_remove_hotelfaqs_hotel_remove_hotelfeatures_hotel_and_more'),
    ]

    operations = [
        migrations.RunPython(align_room_hotel_with_room_type, noop_reverse),
    ]
