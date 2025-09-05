from django.core.management.base import BaseCommand
from menu.models import Category
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Fix empty or duplicate slugs in Category model'

    def handle(self, *args, **options):
        categories = Category.objects.all()
        updated_count = 0

        for category in categories:
            original_slug = category.slug
            
            # If slug is empty, generate one
            if not original_slug:
                new_slug = slugify(category.name)
                if not new_slug:
                    new_slug = "category"
                
                # Ensure the slug is unique
                existing_count = Category.objects.filter(slug__startswith=new_slug).count()
                if existing_count > 0:
                    new_slug = f"{new_slug}-{existing_count + 1}"
                
                category.slug = new_slug
                category.save(update_fields=['slug'])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated empty slug for "{category.name}" to "{new_slug}"'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully fixed {updated_count} categories with empty slugs')) 