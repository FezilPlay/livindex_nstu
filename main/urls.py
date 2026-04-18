from django.urls import path
from . import views
from .views import CountryDetailView, CityDetailView

urlpatterns = [
    path('', views.HomeView.as_view(), name='index'),
    path('map', views.map, name='map'),
    path('purchasing_power_ranking', views.purchasing_power_ranking, name='purchasing_power_ranking'),
    path('work_and_balance', views.work_and_balance, name='work_and_balance'),
    path('work_and_balance_item', views.work_and_balance_item, name='work_and_balance_item'),
    path('healthcare', views.healthcare, name='healthcare'),
    path('categories', views.categories, name='categories'),
    path('inequality', views.inequality, name='inequality'),
    path('inequality_item', views.inequality_item, name='inequality_item'),
    path('api/map/', views.api_map_data, name='api_map_data'),
    # Главная страница хаба (то, что мы сейчас верстали)


    # Страница конкретной страны (куда ведут ссылки из рейтинга)
    # Используем slug, чтобы ссылки были красивыми: /purchasing-power/spain/
    # path('purchasing-power/<slug:country_slug>/', views.country_purchasing_power, name='country_purchasing_power'),


    # Главные страницы разделов (заглушки для ссылок из тумблера)

    path('search/', views.search_destination, name='search'),
    path('htmx/global-ranking/', views.global_ranking_table, name='global_ranking_table'),
    path('htmx/health_ranking/', views.health_ranking_table, name='health_ranking_table'),
    path('htmx/working_hours_ranking_rows/', views.working_hours_ranking_table, name='working_hours_ranking_table'),

    # Режимы для СТРАНЫ
    path('<slug:slug>', CountryDetailView.as_view(), name='country_detail'),

    # ТРИ РЕЖИМА ДЛЯ ГОРОДА (Важно: порядок имеет значение)
    path('<str:country_slug>/<str:slug>', CityDetailView.as_view(), name='city_detail'),
]