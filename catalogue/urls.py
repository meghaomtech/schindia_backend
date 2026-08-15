from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'catalogue-items', views.CatalogueItemViewSet, basename='catalogue-item')
router.register(r'discount-rules', views.DiscountRuleViewSet, basename='discount-rule')

urlpatterns = [
    path('', include(router.urls)),
]
