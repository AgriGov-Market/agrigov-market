from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0019_delete_notification'),
    ]

    operations = [
        migrations.CreateModel(
            name='DismissedNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_id', models.CharField(max_length=50)),
                ('dismissed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dismissed_notifications', to='auth.user')),
            ],
            options={
                'ordering': ['-dismissed_at'],
                'unique_together': {('user', 'notification_id')},
            },
        ),
    ]
