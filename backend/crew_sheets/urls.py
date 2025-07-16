from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CrewSheetViewSet

# Create a router and register our viewset
router = DefaultRouter()
router.register(r'crew-sheets', CrewSheetViewSet, basename='crew-sheet')

# Wire up our API with our router
urlpatterns = [
    path('', include(router.urls)),
]
