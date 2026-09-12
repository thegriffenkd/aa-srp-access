from django.urls import path

from . import views

app_name = "srp_access"

urlpatterns = [
    path("", views.fleet_list, name="fleet_list"),
    path("fleets/<int:fleet_id>/", views.fleet_detail, name="fleet_detail"),
    path("fleets/<int:fleet_id>/request/", views.request_srp, name="request_srp"),
]
