from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Category, Product
from tables.models import Table
from .forms import CategoryForm, ProductForm
from Dalooneh.decorators import superuser_required
from django.http import JsonResponse

@cache_page(60 * 15)  # Cache for 15 minutes
def category_list(request):
    categories = Category.objects.filter(is_active=True)
    
    # Get table info if available
    table = None
    if 'table_token' in request.session:
        table = get_object_or_404(Table, id=request.session.get('table_id'))
    
    return render(request, 'menu/category_list.html', {
        'categories': categories,
        'category': categories.first() if categories.exists() else None,  # Add single category for header
        'table': table
    })

@cache_page(60 * 15)  # Cache for 15 minutes
def public_category_list(request):
    """View for listing categories without requiring table authentication"""
    categories = Category.objects.filter(is_active=True)
    
    # Try to get table info if available (but not required)
    table = None
    if 'table_token' in request.session:
        try:
            table = Table.objects.get(id=request.session.get('table_id'))
        except Table.DoesNotExist:
            pass
    
    return render(request, 'menu/category_list.html', {
        'categories': categories,
        'category': categories.first() if categories.exists() else None,
        'table': table
    })

@cache_page(60 * 15)  # Cache for 15 minutes
def product_list(request, category_id):
    category = get_object_or_404(Category, id=category_id, is_active=True)
    
    # Get filter parameters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    preparation_time = request.GET.get('preparation_time')
    search_query = request.GET.get('q')
    
    # Base queryset
    products = Product.objects.filter(category=category, is_active=True, is_available=True)
    
    # Apply filters
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    if preparation_time:
        products = products.filter(preparation_time__lte=preparation_time)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Get table info if available
    table = None
    if 'table_token' in request.session:
        table = get_object_or_404(Table, id=request.session.get('table_id'))
    
    return render(request, 'menu/product_list.html', {
        'category': category,
        'products': products,
        'table': table,
        'filters': {
            'min_price': min_price,
            'max_price': max_price,
            'preparation_time': preparation_time,
            'search_query': search_query
        }
    })

@cache_page(60 * 15)  # Cache for 15 minutes
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Get table info if available
    table = None
    if 'table_token' in request.session:
        table = get_object_or_404(Table, id=request.session.get('table_id'))
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True,
        is_available=True
    ).exclude(id=product.id)[:4]
    
    return render(request, 'menu/product_detail.html', {
        'product': product,
        'table': table,
        'related_products': related_products
    })

class MenuView(ListView):
    model = Category
    template_name = 'menu/menu.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get table info
        table = None
        if 'table_token' in self.request.session:
            table = get_object_or_404(Table, id=self.request.session.get('table_id'))
        context['table'] = table
        
        # Get featured products
        context['featured_products'] = Product.objects.filter(
            is_active=True,
            is_available=True
        ).order_by('?')[:6]  # Random 6 products
        
        # Get popular categories
        context['popular_categories'] = Category.objects.filter(
            is_active=True
        ).order_by('?')[:4]  # Random 4 categories
        
        return context

class CategoryDetailView(DetailView):
    model = Category
    template_name = 'menu/category_list.html'
    context_object_name = 'category'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get table info
        table = None
        if 'table_token' in self.request.session:
            try:
                table_id = self.request.session.get('table_id')
                table = Table.objects.get(id=table_id)
            except Table.DoesNotExist:
                pass
        context['table'] = table
        
        # Get category products
        context['products'] = self.object.products.filter(
            is_active=True,
            is_available=True
        )
        
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'menu/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get table info
        table = None
        if 'table_token' in self.request.session:
            table = get_object_or_404(Table, id=self.request.session.get('table_id'))
        context['table'] = table
        
        # Get related products
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            is_active=True,
            is_available=True
        ).exclude(id=self.object.id)[:4]
        
        return context

# Management Panel Views
@superuser_required
@login_required
def management_dashboard(request):
    """Dashboard view for the menu management panel."""
    categories_count = Category.objects.count()
    products_count = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    available_products = Product.objects.filter(is_available=True).count()
    
    context = {
        'categories_count': categories_count,
        'products_count': products_count,
        'active_products': active_products,
        'available_products': available_products,
    }
    return render(request, 'menu/management/dashboard.html', context)

@superuser_required
@login_required
def management_category_list(request):
    """List all categories for management."""
    categories = Category.objects.all().order_by('name')
    return render(request, 'menu/management/category_list.html', {'categories': categories})

@superuser_required
@login_required
def management_category_add(request):
    """Add a new category."""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                category = form.save(commit=False)
                # Additional check before saving
                if not category.slug and not form.cleaned_data.get('name'):
                    form.add_error('name', 'Category name cannot be empty.')
                    return render(request, 'menu/management/category_form.html', {
                        'form': form,
                        'title': 'Add New Category'
                    })
                category.save()
                messages.success(request, 'Category created successfully.')
                return redirect('menu:management_category_list')
            except Exception as e:
                form.add_error(None, f'Error creating category: {str(e)}')
    else:
        form = CategoryForm()
    
    return render(request, 'menu/management/category_form.html', {
        'form': form,
        'title': 'Add New Category'
    })

@superuser_required
@login_required
def management_category_edit(request, category_id):
    """Edit an existing category."""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            try:
                category = form.save(commit=False)
                # Additional check before saving
                if not category.slug and not form.cleaned_data.get('name'):
                    form.add_error('name', 'Category name cannot be empty.')
                    return render(request, 'menu/management/category_form.html', {
                        'form': form,
                        'category': category,
                        'title': 'Edit Category'
                    })
                category.save()
                messages.success(request, 'Category updated successfully.')
                return redirect('menu:management_category_list')
            except Exception as e:
                form.add_error(None, f'Error updating category: {str(e)}')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'menu/management/category_form.html', {
        'form': form,
        'category': category,
        'title': 'Edit Category'
    })

@superuser_required
@login_required
def management_category_delete(request, category_id):
    """Delete a category."""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        # Check if category has products
        if category.products.exists():
            messages.error(request, 'Cannot delete a category that has products.')
            return redirect('menu:management_category_list')
        
        category.delete()
        messages.success(request, 'Category deleted successfully.')
        return redirect('menu:management_category_list')
    
    return render(request, 'menu/management/category_confirm_delete.html', {
        'category': category
    })

@superuser_required
@login_required
def management_product_list(request):
    """List all products for management."""
    # Get filter parameters
    category_id = request.GET.get('category')
    is_active = request.GET.get('is_active')
    is_available = request.GET.get('is_available')
    search_query = request.GET.get('q')
    
    # Base queryset
    products = Product.objects.all().order_by('category', 'name')
    
    # Apply filters
    if category_id:
        products = products.filter(category_id=category_id)
    if is_active == 'true':
        products = products.filter(is_active=True)
    elif is_active == 'false':
        products = products.filter(is_active=False)
    if is_available == 'true':
        products = products.filter(is_available=True)
    elif is_available == 'false':
        products = products.filter(is_available=False)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Get all categories for filter dropdown
    categories = Category.objects.all()
    
    return render(request, 'menu/management/product_list.html', {
        'products': products,
        'categories': categories,
        'filters': {
            'category_id': category_id,
            'is_active': is_active,
            'is_available': is_available,
            'search_query': search_query
        }
    })

@superuser_required
@login_required
def management_product_add(request):
    """Add a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product created successfully.')
            return redirect('menu:management_product_list')
    else:
        form = ProductForm()
    
    return render(request, 'menu/management/product_form.html', {
        'form': form,
        'title': 'Add New Product'
    })

@superuser_required
@login_required
def management_product_edit(request, product_id):
    """Edit an existing product."""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('menu:management_product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'menu/management/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Edit Product'
    })

@superuser_required
@login_required
def management_product_delete(request, product_id):
    """Delete a product."""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully.')
        return redirect('menu:management_product_list')
    
    return render(request, 'menu/management/product_confirm_delete.html', {
        'product': product
    })

@superuser_required
@login_required
def toggle_product_status(request, product_id):
    """Toggle the is_active status of a product."""
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save()
    
    # Return the status to refresh just the element
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_active': product.is_active
        })
    
    # Redirect back to the list if not an AJAX request
    return redirect('menu:management_product_list')

@superuser_required
@login_required
def toggle_product_availability(request, product_id):
    """Toggle the is_available status of a product."""
    product = get_object_or_404(Product, id=product_id)
    product.is_available = not product.is_available
    product.save()
    
    # Return the status to refresh just the element
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_available': product.is_available
        })
    
    # Redirect back to the list if not an AJAX request
    return redirect('menu:management_product_list')
