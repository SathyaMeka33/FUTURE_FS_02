from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=25)),
                ("source", models.CharField(max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[("new", "New"), ("contacted", "Contacted"), ("converted", "Converted")],
                        default="new",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(model_name="lead", index=models.Index(fields=["status"], name="leads_lead_status_5eb816_idx")),
        migrations.AddIndex(model_name="lead", index=models.Index(fields=["source"], name="leads_lead_source_bf8ce4_idx")),
        migrations.AddIndex(
            model_name="lead", index=models.Index(fields=["created_at"], name="leads_lead_created_70af72_idx")
        ),
        migrations.AddIndex(model_name="lead", index=models.Index(fields=["email"], name="leads_lead_email_e3488d_idx")),
    ]
