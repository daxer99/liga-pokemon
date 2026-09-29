from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Liga Pokémon TCG · Administración"
admin.site.site_title = "Liga Pokémon TCG"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("torneos.urls")),
]
