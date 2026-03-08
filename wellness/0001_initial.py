# wellness/migrations/0001_initial.py
# Run: python manage.py makemigrations && python manage.py migrate

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='WellnessRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emotion_selected', models.CharField(
                    choices=[('angry','Angry'),('anxious','Anxious'),('stressed','Stressed'),('restless','Restless')],
                    max_length=20, verbose_name='Emotion Selected'
                )),
                ('rating_score', models.PositiveSmallIntegerField(
                    choices=[(0,'0 stars'),(1,'1 star'),(2,'2 stars'),(3,'3 stars'),(4,'4 stars'),(5,'5 stars')],
                    verbose_name='Rating Score (0–5)'
                )),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Submitted At')),
                ('video_ids', models.TextField(blank=True, verbose_name='Video IDs Shown')),
                ('session_key', models.CharField(blank=True, max_length=40, verbose_name='Session Key')),
            ],
            options={'ordering': ['-timestamp'], 'verbose_name': 'Wellness Rating', 'verbose_name_plural': 'Wellness Ratings'},
        ),
    ]
