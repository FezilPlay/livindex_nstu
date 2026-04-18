from django.db import models
from django.db.models import JSONField
import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile


def process_image_to_webp(instance, image_field): # <-- ДОБАВИЛИ аргумент instance
    if not image_field:
        return

    # Формируем идеальное имя файла из slug (например: russia.webp)
    expected_filename = f"{instance.slug}.webp"

    # Если имя файла уже правильное (например, при повторном сохранении), пропускаем
    if image_field.name.endswith(expected_filename):
        return

    img = Image.open(image_field)

    # 1. МЕНЯЕМ РАЗМЕР (Resizing)
    max_width = 1920
    if img.width > max_width:
        output_size = (max_width, int((max_width / img.width) * img.height))
        img = img.resize(output_size, Image.LANCZOS)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    output = BytesIO()

    # 2. ОПТИМИЗИРУЕМ КАЧЕСТВО
    img.save(output, format='WEBP', quality=75, optimize=True)
    output.seek(0)

    # Сохраняем с новым именем, привязанным к стране/городу!
    image_field.save(expected_filename, ContentFile(output.read()), save=False)


class ModeChoices(models.TextChoices):
    STATISTICS = 'stats', 'Статистика'
    RELOCATION = 'relocation', 'Релокация'
    TOURISM = 'tourism', 'Туризм'


# 1. ГЕОГРАФИЯ
class Country(models.Model):
    # ЯЗЫКИ И НАЗВАНИЯ
    name = models.CharField(max_length=100, unique=True, verbose_name='Название (Англ - для ссылок)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название (Рус - для сайта)')

    iso_code = models.CharField(
        max_length=6,
        unique=True,
        verbose_name='ISO Alpha-2 (Код)',
        help_text="Используется для генерации флага (например: 'ru', 'us', 'kz')"
    )
    slug = models.SlugField(unique=True, blank=True, verbose_name='URL-адрес (slug)')
    population = models.BigIntegerField(null=True, blank=True, verbose_name='Население')

    # ИЗОБРАЖЕНИЕ
    image = models.ImageField(upload_to='countries/', null=True, blank=True, verbose_name='Фото обложки')

    latest_metrics = JSONField(default=dict, blank=True, verbose_name='Актуальные метрики (JSON)')

    class Meta:
        verbose_name = 'Страна'
        verbose_name_plural = 'Страны'

    def __str__(self):
        # Если есть русское название — показываем его, иначе английское
        return self.name_ru or self.name

    @property
    def flag_url(self):
        if self.iso_code:
            return f"https://flagcdn.com/{self.iso_code.lower()}.svg"
        return None

    def save(self, *args, **kwargs):
        # Если обновляется только метрика (через DataPoint), не трогаем картинку
        update_fields = kwargs.get('update_fields')
        if update_fields and 'latest_metrics' in update_fields and len(update_fields) == 1:
            return super().save(*args, **kwargs)

        # Конвертируем картинку, если она есть
        if self.image:
            process_image_to_webp(self, self.image)

        super().save(*args, **kwargs)


class City(models.Model):
    # ЯЗЫКИ И НАЗВАНИЯ
    name = models.CharField(max_length=100, verbose_name='Название (Англ - для ссылок)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название (Рус - для сайта)')
    slug = models.SlugField(blank=True, verbose_name='URL-адрес (slug)')

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='cities', verbose_name='Страна')
    population = models.BigIntegerField(null=True, blank=True, verbose_name='Население')
    is_capital = models.BooleanField(default=False, verbose_name='Это столица?')

    # ИЗОБРАЖЕНИЕ
    image = models.ImageField(upload_to='cities/', null=True, blank=True, verbose_name='Фото обложки')

    latest_metrics = JSONField(
        default=dict,
        blank=True,
        verbose_name='Метрики по годам (gdp_ppp_2025, gdp_ppp_2026...)'
    )

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        unique_together = ('name', 'country')

    def __str__(self):
        city_name = self.name_ru or self.name
        country_name = self.country.name_ru or self.country.name
        return f"{city_name} ({country_name})"

    def save(self, *args, **kwargs):
        # Если обновляется только метрика (через DataPoint), не трогаем картинку
        update_fields = kwargs.get('update_fields')
        if update_fields and 'latest_metrics' in update_fields and len(update_fields) == 1:
            return super().save(*args, **kwargs)

        # Конвертируем картинку, если она есть
        if self.image:
            process_image_to_webp(self, self.image) # <-- ПЕРЕДАЕМ self (сам объект)

        super().save(*args, **kwargs)


class IndicatorCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название категории')
    slug = models.SlugField(unique=True, verbose_name='URL-адрес (slug)')

    class Meta:
        verbose_name = 'Категория показателя'
        verbose_name_plural = 'Категории показателей'

    def __str__(self):
        return self.name


class Indicator(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name='Код показателя')
    name = models.CharField(max_length=200, verbose_name='Название')
    category = models.ForeignKey(IndicatorCategory, on_delete=models.PROTECT, related_name='indicators',
                                 verbose_name='Категория')
    unit = models.CharField(max_length=30, blank=True, verbose_name='Единицы измерения')
    higher_better = models.BooleanField(default=True, verbose_name='Выше — лучше?')
    source = models.CharField(max_length=150, blank=True, verbose_name='Источник по умолчанию')
    global_min = models.FloatField(null=True, blank=True, verbose_name='Глобальный минимум')
    global_max = models.FloatField(null=True, blank=True, verbose_name='Глобальный максимум')

    class Meta:
        verbose_name = 'Показатель'
        verbose_name_plural = 'Показатели'

    def __str__(self):
        return self.name


# 3. ХРАНИЛИЩЕ ДАННЫХ
class DataPoint(models.Model):
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, verbose_name='Показатель')
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Страна')
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Город')
    year = models.IntegerField(verbose_name='Год')
    value = models.FloatField(verbose_name='Значение')
    specific_source = models.CharField(max_length=150, blank=True, verbose_name='Специфический источник')

    class Meta:
        verbose_name = 'Значение'
        verbose_name_plural = 'Значения'
        unique_together = ('indicator', 'country', 'city', 'year')
        indexes = [
            models.Index(fields=['country', 'year']),
            models.Index(fields=['city', 'year']),
        ]

    def __str__(self):
        location = self.city.name_ru or self.city.name if self.city else (
            self.country.name_ru or self.country.name if self.country else 'Неизвестно')
        return f"{self.indicator.name} - {location} ({self.year})"

    @property
    def effective_source(self):
        return self.specific_source or self.indicator.source

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        location = self.city or self.country
        if location:
            metrics = getattr(location, 'latest_metrics', {}) or {}

            # Новый формат: gdp_ppp_2025, population_2024 и т.д.
            key = f"{self.indicator.code}_{self.year}"
            metrics[key] = self.value

            location.latest_metrics = metrics
            location.save(update_fields=['latest_metrics'])


# 4. РЕЖИМЫ И НАСТРОЙКИ ВЫВОДОВ
class ModeIndicatorWeight(models.Model):
    mode = models.CharField(max_length=20, choices=ModeChoices.choices, verbose_name='Режим')
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, verbose_name='Показатель')
    weight = models.FloatField(default=1.0, verbose_name='Вес (Множитель)')

    class Meta:
        verbose_name = 'Вес показателя'
        verbose_name_plural = 'Веса показателей для режимов'
        unique_together = ('mode', 'indicator')

    def __str__(self):
        return f"{self.get_mode_display()} -> {self.indicator.name} (x{self.weight})"


class TextInsight(models.Model):
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Страна')
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Город')
    mode = models.CharField(max_length=20, choices=ModeChoices.choices, verbose_name='Режим')
    summary = models.TextField(max_length=200, verbose_name='Короткий вывод')

    class Meta:
        verbose_name = 'Информация (страница)'
        verbose_name_plural = 'Информация (страница)'
        unique_together = ('country', 'city', 'mode')

    def __str__(self):
        location = self.city.name_ru or self.city.name if self.city else (
            self.country.name_ru or self.country.name if self.country else 'Неизвестно')
        return f"Инсайт: {location}[{self.get_mode_display()}]"