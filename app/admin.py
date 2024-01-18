from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from app.models import Domain, Tenant

# Register domain model
admin.site.register(Domain)

# Register tenant model
@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', )
