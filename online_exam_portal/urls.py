from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('', include('apps.exams.urls')),
    path('', include('apps.students.urls')),
    path('', include('apps.teachers.urls')),

    # ERP Foundation CRUD
    path('centers/', include('apps.centers.urls')),
    path('courses/', include('apps.courses.urls')),
    path('batches/', include('apps.batches.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('fees/', include('apps.fees.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
