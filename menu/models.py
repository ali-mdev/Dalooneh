from django.db import models
from django.utils.text import slugify
from tables.models import Table


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Category Name')
    description = models.TextField(blank=True, verbose_name='Description')
    image = models.ImageField(upload_to='categories/', blank=True, verbose_name='Image')
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            original_slug = slugify(self.name)
            if not original_slug:  # If slugify returns empty string
                original_slug = "category"

            # Ensure the slug is unique
            queryset = Category.objects.filter(slug__startswith=original_slug)
            if queryset.exists():
                # If there are existing slugs starting with the same prefix,
                # add a numerical suffix to make it unique
                count = queryset.count()
                self.slug = f"{original_slug}-{count + 1}"
            else:
                self.slug = original_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Category')
    name = models.CharField(max_length=200, verbose_name='Product Name')
    description = models.TextField(verbose_name='Description')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Price')
    image = models.ImageField(upload_to='products/', blank=True, verbose_name='Image')
    is_available = models.BooleanField(default=True, verbose_name='Available')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    preparation_time = models.PositiveIntegerField(default=15, verbose_name='Preparation Time (minutes)')
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            original_slug = slugify(self.name)
            if not original_slug:  # If slugify returns empty string
                original_slug = "product"

            # Ensure the slug is unique
            queryset = Product.objects.filter(slug__startswith=original_slug)
            if self.pk:  # If this is an update, exclude current instance
                queryset = queryset.exclude(pk=self.pk)

            if queryset.exists():
                # If there are existing slugs starting with the same prefix,
                # add a numerical suffix to make it unique
                count = queryset.count()
                self.slug = f"{original_slug}-{count + 1}"
            else:
                self.slug = original_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name