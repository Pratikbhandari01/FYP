from django.db import migrations, models
import django.db.models.deletion
import shortuuid.django_fields


def sync_booking_status_from_payment_status(apps, schema_editor):
    Booking = apps.get_model('hotel', 'Booking')

    Booking.objects.filter(payment_status='completed').update(booking_status='paid')
    Booking.objects.filter(payment_status='cancelled').update(booking_status='cancelled')


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0012_review_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='booking_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('paid', 'Paid'), ('cancelled', 'Cancelled')],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='guests',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='booking',
            name='payment_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('completed', 'Paid'), ('failed', 'Failed'), ('cancelled', 'Cancelled')],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_id', shortuuid.django_fields.ShortUUIDField(alphabet=None, blank=True, length=10, max_length=10, prefix='', unique=True)),
                ('payment_method', models.CharField(default='khalti', max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('transaction_id', models.CharField(blank=True, max_length=120)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='hotel.booking')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(sync_booking_status_from_payment_status, migrations.RunPython.noop),
    ]
