from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenRefreshView,
)
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="PC Builder API",
      default_version='v1',
      description="API documentation for PC Builder",
      terms_of_service="https://www.yourapp.com/terms/",
      contact=openapi.Contact(email="contact@yourapp.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),              
    path('api/v1/', include('pcbuilder.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('api/v1/logout/', TokenBlacklistView.as_view(), name='token_blacklist'), 
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Swagger UI:
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # ReDoc UI (optional alternative to Swagger):
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
