"""
Migration 0005 — pivot to video-specific feedback models.

Changes:
  - Delete WellnessRating (old emotion-level rating)
  - Delete Comment (old per-video comment, replaced below)
  - Delete VideoRating (old version — recreated with nullable user + UniqueConstraint)
  - Create VideoRating (new, nullable user, UniqueConstraint instead of unique_together)
  - Create VideoComment (new, replaces Comment with nullable user)
"""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wellness', '0004_emailverification'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── Remove old models ───────────────────────────────────────────────
        migrations.DeleteModel(name='WellnessRating'),
        migrations.DeleteModel(name='Comment'),
        migrations.DeleteModel(name='VideoRating'),

        # ── Create new VideoRating ──────────────────────────────────────────
        migrations.CreateModel(
            name='VideoRating',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True,
                                                    serialize=False, verbose_name='ID')),
                ('video_id',    models.CharField(db_index=True, max_length=20)),
                ('video_title', models.CharField(blank=True, max_length=255)),
                ('score',       models.PositiveSmallIntegerField(
                                    choices=[(1,'1 star'),(2,'2 stars'),(3,'3 stars'),
                                             (4,'4 stars'),(5,'5 stars')])),
                ('created_at',  models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('user',        models.ForeignKey(
                                    blank=True, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='video_ratings',
                                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Video Rating',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='videorating',
            constraint=models.UniqueConstraint(
                condition=models.Q(user__isnull=False),
                fields=['user', 'video_id'],
                name='unique_user_video_rating',
            ),
        ),

        # ── Create new VideoComment ─────────────────────────────────────────
        migrations.CreateModel(
            name='VideoComment',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True,
                                                    serialize=False, verbose_name='ID')),
                ('video_id',    models.CharField(db_index=True, max_length=20)),
                ('video_title', models.CharField(blank=True, max_length=255)),
                ('body',        models.TextField(max_length=500)),
                ('created_at',  models.DateTimeField(default=django.utils.timezone.now)),
                ('user',        models.ForeignKey(
                                    blank=True, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='video_comments',
                                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Video Comment',
                'ordering': ['-created_at'],
            },
        ),
    ]
