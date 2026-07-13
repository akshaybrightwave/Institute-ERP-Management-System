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
    path('categories/', include('apps.categories.urls')),
    path('batches/', include('apps.batches.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('fees/', include('apps.fees.urls')),
    path('certificates/', include('apps.certificates.urls')),
    path('reports/', include('apps.reports.urls')),
    path('management/', include('apps.management.urls')),
    path('hr/', include('apps.hr.urls')),
    path('subjects/', include('apps.subjects.urls')),
    path('academics/', include('apps.academics.urls')),
    path('admit-cards/', include('apps.admit_card.urls')),
    path('results/', include('apps.results.urls')),
    path('study-materials/', include('apps.study_material.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
