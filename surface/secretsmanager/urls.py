from django.urls import path
from . import views

urlpatterns = [
    path('', views.secret_list, name='secret_list'),
    path('<int:pk>/', views.secret_detail, name='secret_detail'),
]