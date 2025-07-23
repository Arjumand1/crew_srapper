from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CrewSheetViewSet

# Create a router and register our viewset with explicit routes
router = DefaultRouter()
router.register(r'crew-sheets', CrewSheetViewSet, basename='crew-sheet')

# Instead of registering the custom actions separately, let's use router.urls to expose all actions
urlpatterns = [
    path('', include(router.urls)),
]
