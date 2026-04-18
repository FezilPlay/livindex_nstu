from django.shortcuts import render
from django.conf import settings
from django.templatetags.static import static
from django.views.generic import DetailView, TemplateView
from .models import Country, City, TextInsight, Indicator, DataPoint
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .services.calculators import liveindexCalculator  # Импорт сервиса
import traceback


def get_latest_metric(metrics, prefix):
    if not metrics:
        return None, None

    found = []
    for key, value in metrics.items():
        if key.startswith(prefix + "_"):
            try:
                year = int(key.rsplit("_", 1)[-1])
                found.append((year, value))
            except ValueError:
                continue

    if not found:
        return None, None

    found.sort(key=lambda x: x[0], reverse=True)
    return found[0][1], found[0][0]


class HomeView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        slugs = ['russia', 'united-states', 'china']
        countries = sorted(
            Country.objects.filter(slug__in=slugs),
            key=lambda x: slugs.index(x.slug)
        )

        cards = []
        for country in countries:
            metrics = country.latest_metrics or {}

            gdp_value, gdp_year = get_latest_metric(metrics, "gdp_ppp")
            life_value, life_year = get_latest_metric(metrics, "life_expectancy")
            hours_value, hours_year = get_latest_metric(metrics, "working_hours_per_worker")

            cards.append({
                "country": country,
                "gdp_value": gdp_value,
                "gdp_year": gdp_year,
                "life_value": life_value,
                "life_year": life_year,
                "hours_value": hours_value,
                "hours_year": hours_year,
            })

        context["cards"] = cards
        return context



def purchasing_power_item(request):
    context = {
        'title': 'liveindex — Страна',
    }
    return render(request, 'purchasing_power_item.html', context)


def purchasing_power(request):
    context = {
        'title': 'liveindex — Покупательная способность',
    }
    return render(request, 'purchasing_power.html', context)


def categories(request):
    context = {
        'title': 'liveindex — Категории',
    }
    return render(request, 'categories.html', context)


def purchasing_power_ranking(request):
    context = {
        'title': 'liveindex —  рейтинг',
    }
    return render(request, 'purchasing_power_ranking.html', context)


def work_and_balance(request):
    context = {
        'title': 'liveindex — Работа и баланс',
    }
    return render(request, 'work_and_balance.html', context)


def work_and_balance_item(request):
    context = {
        'title': 'liveindex — Работа и баланс',
    }
    return render(request, 'work_and_balance_item.html', context)


def social_security(request):
    context = {
        'title': 'liveindex — соц',
    }
    return render(request, 'social_security.html', context)


def social_security_item(request):
    context = {
        'title': 'liveindex — соц',
    }
    return render(request, 'social_security_item.html', context)


def healthcare(request):
    context = {
        'title': 'liveindex — соц',
    }
    return render(request, 'healthcare.html', context)


def healthcare_item(request):
    context = {
        'title': 'liveindex — соц',
    }
    return render(request, 'healthcare_item.html', context)



def inequality(request):
    context = {
        'title': 'liveindex — соц',
    }
    return render(request, 'inequality.html', context)


def inequality_item(request):
    context = {
        'title': 'liveindex — соц',
    }
    return render(request, 'inequality_item.html', context)


def map(request):
    context = {
        'title': 'ВВП (ППС) на душу населения (в международных долларах)',
    }
    return render(request, 'map.html', context)


class CountryDetailView(DetailView):
    model = Country
    template_name = 'item_relocation_country.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_latest_datapoint(self, country, indicator_code):
        return (
            DataPoint.objects
            .filter(country=country, indicator__code=indicator_code)
            .select_related('indicator')
            .order_by('-year')
            .first()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Описание страны, если нужно
        context['insight'] = TextInsight.objects.filter(country=self.object).first()

        # Последний год можно брать из параметра URL, либо оставить 2026
        year = int(self.request.GET.get('year', 2023))
        context['year'] = year

        # Если нужны все datapoints за год
        context['data_points'] = self.object.datapoint_set.filter(year=year)

        # Три нужных показателя
        life_exp = self.get_latest_datapoint(self.object, 'life_expectancy')
        work_hours = self.get_latest_datapoint(self.object, 'working_hours_per_worker')
        gdp = self.get_latest_datapoint(self.object, 'gdp_ppp')

        context['latest_stats'] = {
            'life_expectancy': life_exp,
            'working_hours': work_hours,
            'gdp': gdp,
        }

        # Если эти функции ещё нужны
        context['salary_minus_rent'] = liveindexCalculator.salary_minus_rent(self.object, year)
        context['quality_index'] = liveindexCalculator.quality_of_life_index(self.object, year)
        context['cities'] = self.object.cities.all()

        return context


class CityDetailView(DetailView):
    model = City
    template_name = 'item_relocation_city.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        country_slug = self.kwargs.get('country_slug')
        city_slug = self.kwargs.get('slug')
        return get_object_or_404(City, country__slug=country_slug, slug=city_slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Определяем режим для тумблера
        url_name = self.request.resolver_match.url_name
        mode_mapping = {
            'city_stat': 'stat',
            'city_tour': 'tour',
            'city_relo': 'relo',
            'city_detail': 'stat',
        }
        context['active_mode'] = mode_mapping.get(url_name, 'stat')

        # 2. Генерируем ссылки для тумблера (учитываем два слага!)
        url_kwargs = {'country_slug': self.object.country.slug, 'slug': self.object.slug}
        context['stat_url'] = reverse('city_stat', kwargs=url_kwargs)
        context['tour_url'] = reverse('city_tour', kwargs=url_kwargs)
        context['relo_url'] = reverse('city_relo', kwargs=url_kwargs)

        # 3. Данные и расчеты
        year = self.request.GET.get('year', 2026)
        context['data_points'] = self.object.datapoint_set.filter(year=year)
        context['salary_minus_rent'] = liveindexCalculator.salary_minus_rent(self.object, year)
        context['quality_index'] = liveindexCalculator.quality_of_life_index(self.object, year)
        context['country'] = self.object.country

        return context


def working_hours_ranking_table(request):
    """
    HTMX-частичный view для рейтинга «Рабочие часы»
    Полностью по аналогии с health_ranking_table
    """
    indicator_code = request.GET.get('indicator', 'working_hours_per_worker')
    order = request.GET.get('order', 'asc')      # меньше часов = лучше
    sort_by = request.GET.get('sort_by', 'value')

    YEAR = 2023
    metric_key = f"{indicator_code}_{YEAR}"

    countries_qs = Country.objects.all()
    country_list = list(countries_qs)

    # ФИЛЬТРАЦИЯ: только страны с данными по рабочим часам
    country_list = [
        c for c in country_list
        if c.latest_metrics and metric_key in c.latest_metrics
    ]

    # === РАСЧЁТЫ В PYTHON (как combined_health_index в медицине) ===
    for country in country_list:
        hours = country.latest_metrics.get(metric_key, 0)
        country.hours_year = hours
        country.hours_week = round(hours / 52, 1) if hours > 0 else 0
        # Прогресс-бар (чем меньше часов — тем уже заливка, максимум 2500 часов ≈ 100%)
        country.progress_width = min(100, int(hours / 25)) if hours > 0 else 0

    # Сортировка
    if sort_by == 'name':
        country_list.sort(
            key=lambda x: (x.name_ru or x.name).lower(),
            reverse=(order == 'desc')
        )
    else:
        # По умолчанию — по часам в год (asc = меньше часов сверху)
        country_list.sort(
            key=lambda x: x.hours_year,
            reverse=(order == 'desc')
        )

    top_country = country_list[0] if country_list else None

    return render(request, 'includes/working_hours_ranking_rows.html', {
        'countries': country_list,
        'top_country': top_country,
        'metric_key': metric_key,
        'total_count': len(country_list),
    })


def global_ranking_table(request):
    # Получаем параметры из URL
    indicator_code = request.GET.get('indicator', 'gdp_ppp')
    order = request.GET.get('order', 'desc')
    sort_by = request.GET.get('sort_by', 'value')

    # === НОВОЕ: фиксируем год 2026 (как у тебя в шапке "2026 Актуально") ===
    YEAR = 2026
    metric_key = f"{indicator_code}_{YEAR}"          # ← теперь gdp_ppp_2026

    countries_qs = Country.objects.all()
    total_count = countries_qs.count()

    indicator = Indicator.objects.filter(code=indicator_code).first()
    unit = indicator.unit if indicator else ""

    country_list = list(countries_qs)

    # ЛОГИКА СОРТИРОВКИ
    if sort_by == 'name':
        country_list.sort(
            key=lambda x: (x.name_ru or x.name).lower(),
            reverse=(order == 'desc')
        )
    else:
        # Сортируем по новому ключу metric_key
        country_list.sort(
            key=lambda x: x.latest_metrics.get(metric_key, 0) or 0,
            reverse=(order == 'desc')
        )

    return render(request, 'includes/global_ranking_rows.html', {
        'countries': country_list,
        'indicator_code': indicator_code,   # оставляем для ссылок сортировки
        'metric_key': metric_key,           # ← НОВОЕ: передаём правильный ключ
        'current_order': order,
        'current_sort': sort_by,
        'total_count': total_count,
        'unit': unit,
    })


def health_ranking_table(request):
    indicator_code = request.GET.get('indicator', 'life_expectancy')
    order = request.GET.get('order', 'desc')
    sort_by = request.GET.get('sort_by', 'value')

    YEAR_LIFE = 2023
    YEAR_HEALTH = 2025

    metric_key = f"{indicator_code}_{YEAR_LIFE}"           # life_expectancy_2023
    health_index_key = f"health_index_{YEAR_HEALTH}"       # health_index_2025

    countries_qs = Country.objects.all()
    country_list = list(countries_qs)

    # === ФИЛЬТРАЦИЯ: только страны с Health Index ===
    country_list = [
        c for c in country_list
        if c.latest_metrics and health_index_key in c.latest_metrics
    ]

    # === НОВОЕ: считаем сводный Индекс здоровья (0-100) ===
    for country in country_list:
        health = country.latest_metrics.get(health_index_key, 0)
        life = country.latest_metrics.get(metric_key, 0)
        country.combined_health_index = round((health + life) / 2, 1)   # ← главное!

    # Сортировка
    if sort_by == 'name':
        country_list.sort(
            key=lambda x: (x.name_ru or x.name).lower(),
            reverse=(order == 'desc')
        )
    else:
        # По умолчанию сортируем по сводному индексу
        country_list.sort(
            key=lambda x: getattr(x, 'combined_health_index', 0),
            reverse=(order == 'desc')
        )

    top_country = country_list[0] if country_list else None

    return render(request, 'includes/health_ranking_rows.html', {
        'countries': country_list,
        'top_country': top_country,
        'metric_key': metric_key,
        'health_index_key': health_index_key,
        'total_count': len(country_list),
    })


def search_destination(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        q = query.casefold()

        # Страны
        for country in Country.objects.all():
            name = (country.name or "").casefold()
            name_ru = (country.name_ru or "").casefold()

            if q in name or q in name_ru:
                results.append({
                    "title": country.name_ru or country.name,
                    "slug": country.slug,
                    "type": "country",
                    "flag_url": country.flag_url,
                    "country_slug": None
                })

                if len(results) >= 5:
                    break

        # Города
        if len(results) < 5:
            for city in City.objects.select_related("country").all():
                name = (city.name or "").casefold()
                name_ru = (city.name_ru or "").casefold()

                if q in name or q in name_ru:
                    results.append({
                        "title": city.name_ru or city.name,
                        "subtitle": city.country.name_ru or city.country.name,
                        "slug": city.slug,
                        "type": "city",
                        "image_url": city.image.url if city.image else None,
                        "country_slug": city.country.slug
                    })

                    if len(results) >= 5:
                        break

    return JsonResponse(results, safe=False)


def api_map_data(request):
    try:
        indicator_code = request.GET.get('indicator', 'gdp_ppp')
        countries = Country.objects.all()

        data = {}
        for country in countries:
            # Проверяем, что метрики существуют и это словарь
            metrics = country.latest_metrics

            if metrics and isinstance(metrics, dict):
                value = metrics.get(indicator_code)
                if value is not None:
                    # ВАЖНО: Делаем код страны ВСЕГДА большими буквами (PT, а не pt)
                    # Иначе JS на фронтенде его не узнает!
                    iso_key = str(country.iso_code).upper()
                    data[iso_key] = value

        return JsonResponse(data)

    except Exception as e:
        # Если будет ошибка, мы выведем её в терминале Django
        print("🔥 ОШИБКА В API КАРТЫ:")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)