from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Country, City, IndicatorCategory, Indicator,
    DataPoint, ModeIndicatorWeight, TextInsight
)


class CityInline(admin.TabularInline):
    model = City
    extra = 1
    # Добавили name_ru в инлайн
    fields = ('name', 'name_ru', 'slug', 'population', 'is_capital')


class DataPointResource(resources.ModelResource):
    class Meta:
        model = DataPoint
        fields = (
            'id', 'country__iso_code', 'city__name', 'indicator__code',
            'year', 'value', 'specific_source'
        )
        import_id_fields = ('country', 'city', 'indicator', 'year')


# 1. ГЕОГРАФИЯ
@admin.register(Country)
class CountryAdmin(ImportExportModelAdmin):
    inlines = [CityInline]
    # ДОБАВИЛИ 'has_image' В МАССИВ
    list_display = ('get_display_name', 'has_image', 'iso_code', 'slug', 'population', 'get_capital')
    search_fields = ('name', 'name_ru', 'iso_code')
    list_filter = ('population',)
    prepopulated_fields = {'slug': ('name',)}

    actions = ['update_latest_metrics']

    # --- НОВЫЙ МЕТОД ДЛЯ ГАЛОЧКИ ---
    @admin.display(boolean=True, description='🖼️ Картинка')
    def has_image(self, obj):
        # Если картинка есть, вернет True (зеленая галочка), иначе False (красный крестик)
        return bool(obj.image)

    @admin.display(description='Название')
    def get_display_name(self, obj):
        return f"{obj.name_ru} ({obj.name})" if obj.name_ru else obj.name

    def update_latest_metrics(self, request, queryset):
        updated_count = 0
        for country in queryset:
            self._update_metrics(country)
            updated_count += 1
        self.message_user(request, f'✅ Метрики обновлены для {updated_count} стран')

    update_latest_metrics.short_description = "🔄 Обновить Актуальные метрики (latest_metrics)"

    def _update_metrics(self, country):
        metrics = {}
        for dp in DataPoint.objects.filter(country=country).select_related('indicator'):
            key = f"{dp.indicator.code}_{dp.year}"
            metrics[key] = dp.value

        country.latest_metrics = metrics
        country.save(update_fields=['latest_metrics'])

    @admin.display(description='Столица')
    def get_capital(self, obj):
        capital = obj.cities.filter(is_capital=True).first()
        if capital:
            return capital.name_ru or capital.name
        return "—"


    @admin.register(City)
    class CityAdmin(ImportExportModelAdmin):
        # ДОБАВИЛИ 'has_image' В МАССИВ
        list_display = ('get_display_name', 'country', 'has_image', 'slug', 'population', 'is_capital')
        search_fields = ('name', 'name_ru', 'country__name', 'country__name_ru')
        list_filter = ('country', 'is_capital')
        prepopulated_fields = {'slug': ('name',)}

        actions = ['update_latest_metrics']

        # --- НОВЫЙ МЕТОД ДЛЯ ГАЛОЧКИ ---
        @admin.display(boolean=True, description='🖼️ Картинка')
        def has_image(self, obj):
            return bool(obj.image)

        @admin.display(description='Название')
        def get_display_name(self, obj):
            return f"{obj.name_ru} ({obj.name})" if obj.name_ru else obj.name

        def update_latest_metrics(self, request, queryset):
            updated_count = 0
            for city in queryset:
                self._update_metrics(city)
                updated_count += 1
            self.message_user(request, f'✅ Метрики обновлены для {updated_count} городов')

        update_latest_metrics.short_description = "🔄 Обновить Актуальные метрики (latest_metrics)"

        def _update_metrics(self, city):
            metrics = {}
            for dp in DataPoint.objects.filter(city=city).select_related('indicator'):
                key = f"{dp.indicator.code}_{dp.year}"
                metrics[key] = dp.value

            city.latest_metrics = metrics
            city.save(update_fields=['latest_metrics'])


# 2. МЕТАДАННЫЕ ПОКАЗАТЕЛЕЙ
@admin.register(IndicatorCategory)
class IndicatorCategoryAdmin(ImportExportModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class DataPointInline(admin.TabularInline):
    model = DataPoint
    extra = 0
    fields = ('country', 'city', 'year', 'value')
    autocomplete_fields = ['country', 'city']


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'code')
    list_filter = ('category',)


# 3. ХРАНИЛИЩЕ ДАННЫХ
@admin.register(DataPoint)
class DataPointAdmin(ImportExportModelAdmin):
    resource_class = DataPointResource
    list_display = (
        'get_category', 'indicator', 'country', 'city', 'year', 'value', 'specific_source'
    )
    list_filter = (
        ('indicator__category', admin.RelatedOnlyFieldListFilter),
        ('indicator', admin.RelatedOnlyFieldListFilter),
        'year',
    )
    list_select_related = ('indicator', 'indicator__category', 'country', 'city')
    search_fields = (
    'indicator__name', 'country__name', 'country__name_ru', 'city__name', 'city__name_ru', 'specific_source')
    raw_id_fields = ('country', 'city', 'indicator')

    @admin.display(ordering='indicator__category', description='Категория')
    def get_category(self, obj):
        return obj.indicator.category.name

    @admin.display(description='Итоговый источник')
    def get_effective_source_display(self, obj):
        return obj.effective_source


# 4. РЕЖИМЫ И НАСТРОЙКИ
@admin.register(ModeIndicatorWeight)
class ModeIndicatorWeightAdmin(admin.ModelAdmin):
    list_display = ('mode', 'indicator', 'weight')
    list_filter = ('mode',)
    search_fields = ('indicator__name',)


@admin.register(TextInsight)
class TextInsightAdmin(admin.ModelAdmin):
    list_display = ('get_location', 'mode')
    list_filter = ('mode',)
    search_fields = ('country__name', 'country__name_ru', 'city__name', 'city__name_ru')

    @admin.display(description='Локация')
    def get_location(self, obj):
        if obj.city:
            city_name = obj.city.name_ru or obj.city.name
            country_name = obj.country.name_ru or obj.country.name
            return f"{city_name} ({country_name})"
        if obj.country:
            return obj.country.name_ru or obj.country.name
        return "Неизвестно"


admin.site.site_header = "liveindex — Панель управления"
admin.site.site_title = "liveindex Admin"
admin.site.index_title = "Добро пожаловать в админку liveindex"