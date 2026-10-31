from django.shortcuts import render

def index(request):
    """SaaS products catalog foundation view."""
    products = [
        {'code': 'PRD-CLOUD', 'name': 'Brightloop Cloud Platform', 'category': 'Infrastructure', 'plans_count': 3, 'status': 'Active'},
        {'code': 'PRD-ANALYTICS', 'name': 'Brightloop Analytics Suite', 'category': 'Data & BI', 'plans_count': 2, 'status': 'Active'},
        {'code': 'PRD-SECURITY', 'name': 'Brightloop Secure Shield', 'category': 'Cybersecurity', 'plans_count': 3, 'status': 'Active'},
    ]
    return render(request, 'products/index.html', {
        'page_title': 'Products Catalog',
        'active_tab': 'products',
        'products': products,
    })
