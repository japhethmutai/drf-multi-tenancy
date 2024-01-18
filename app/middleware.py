from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpResponseNotFound, Http404, JsonResponse
from django.db import connection
from django.urls import set_urlconf
from django.utils.deprecation import MiddlewareMixin
from django_tenants.utils import (
    get_public_schema_name,
    get_public_schema_urlconf,
    get_tenant_types,
    has_multi_type_tenants,
    remove_www,
)
from app.models import Tenant


class TenantMainMiddleware(MiddlewareMixin):
    TENANT_NOT_FOUND_EXCEPTION = Http404

    @staticmethod
    def hostname_from_request(request):
        return remove_www(request.get_host().split(":")[0])

    def process_request(self, request):
        connection.set_schema_to_public()
        try:
            hostname = self.hostname_from_request(request)
        except DisallowedHost:
            return HttpResponseNotFound()

        # Check the Tenant from headers to change the schema for each request.
        tenant_name = request.headers.get("Tenant-Header")
        try:
            tenant = Tenant.objects.get(name__iexact=tenant_name)
        except Tenant.DoesNotExist:
            if tenant_name != "public":
                return JsonResponse({"detail": "Tenant not found"}, status=400)
            self.no_tenant_found(request, hostname)
            # If no tenant is found, then set to public Tenant and return
            return

        tenant.domain_url = hostname
        request.tenant = tenant
        connection.set_tenant(request.tenant)
        self.setup_url_routing(request)

    def no_tenant_found(self, request, hostname):
        if (
            hasattr(settings, "SHOW_PUBLIC_IF_NO_TENANT_FOUND")
            and settings.SHOW_PUBLIC_IF_NO_TENANT_FOUND
        ):
            self.setup_url_routing(request=request, force_public=True)
        else:
            raise self.TENANT_NOT_FOUND_EXCEPTION(
                'No tenant for hostname "%s"' % hostname
            )

    @staticmethod
    def setup_url_routing(request, force_public=False):
        public_schema_name = get_public_schema_name()
        if has_multi_type_tenants():
            tenant_types = get_tenant_types()
            if not hasattr(request, "tenant") or (
                force_public
                or request.tenant.schema_name == get_public_schema_name()
            ) and "URLCONF" in tenant_types[public_schema_name]:
                request.urlconf = get_public_schema_urlconf()
            else:
                tenant_type = request.tenant.get_tenant_type()
                request.urlconf = tenant_types[tenant_type]["URLCONF"]
                set_urlconf(request.urlconf)
        else:
            # Do we have a public-specific urlconf?
            if (
                hasattr(settings, "PUBLIC_SCHEMA_URLCONF")
                and (force_public or request.tenant.schema_name == get_public_schema_name())
            ):
                request.urlconf = settings.PUBLIC_SCHEMA_URLCONF
