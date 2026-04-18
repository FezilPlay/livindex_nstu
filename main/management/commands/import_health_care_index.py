import csv
import pycountry
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from ...models import Country, Indicator, IndicatorCategory, DataPoint


class Command(BaseCommand):
    help = 'Импорт Health Care Index — улучшенная версия под твой формат CSV'

    def handle(self, *args, **options):
        csv_file = 'health_care_index.csv'

        # === 1. Показатель (код именно health_index — чтобы совпадало с твоим views.py) ===
        category, _ = IndicatorCategory.objects.get_or_create(
            name='Здравоохранение', slug='healthcare'
        )

        indicator, created = Indicator.objects.get_or_create(
            code='health_index',                                      # ← важно!
            defaults={
                'name': 'Индекс качества здравоохранения (Health Care Index)',
                'category': category,
                'unit': 'баллов (0-100)',
                'source': 'Numbeo / WHO',
                'higher_better': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Создан показатель: {indicator.name}'))

        # === 2. Подтверждение ===
        self.stdout.write(self.style.WARNING(f'\nФайл: {csv_file}'))
        self.stdout.write(self.style.WARNING('Пытаемся читать как CSV с разделителями , и ;'))
        if input('Продолжить? (y/n): ').lower() != 'y':
            self.stdout.write(self.style.ERROR('Отменено.'))
            return

        # === 3. Чтение файла с отладкой ===
        try:
            with open(csv_file, encoding='utf-8', errors='ignore', newline='') as f:
                content = f.read(500)  # первые 500 символов для отладки
                self.stdout.write(self.style.SUCCESS(f'Первые символы файла:\n{content[:300]}...'))

                f.seek(0)
                # Пробуем два самых частых разделителя
                for delimiter in [',', ';', '\t']:
                    f.seek(0)
                    reader = csv.reader(f, delimiter=delimiter)
                    header = next(reader, None)
                    self.stdout.write(self.style.SUCCESS(f'Пробуем разделитель "{delimiter}" → Заголовок: {header}'))

                    total_processed = total_created = total_updated = skipped = 0
                    YEAR = 2025

                    for row_num, row in enumerate(reader, start=2):
                        if len(row) < 2:
                            skipped += 1
                            continue

                        entity = row[0].strip().replace('"', '').replace("'", "")
                        val_raw = row[1].strip().replace('"', '').replace("'", "")

                        self.stdout.write(f'  Строка {row_num}: "{entity}" → {val_raw}')  # отладка

                        if not entity or not val_raw:
                            skipped += 1
                            continue

                        try:
                            value = float(val_raw.replace(',', '.'))
                        except ValueError:
                            skipped += 1
                            continue

                        # Поиск страны
                        try:
                            country_obj = pycountry.countries.search_fuzzy(entity)[0]
                            iso = country_obj.alpha_2.lower()
                        except:
                            self.stdout.write(self.style.WARNING(f'⚠️ Не найдена страна: {entity}'))
                            skipped += 1
                            continue

                        # Страна
                        country, _ = Country.objects.get_or_create(
                            iso_code=iso,
                            defaults={'name': entity, 'slug': slugify(entity)}
                        )
                        if country.name != entity:
                            country.name = entity
                            country.slug = slugify(entity)
                            country.save(update_fields=['name', 'slug'])

                        # DataPoint
                        dp, created_dp = DataPoint.objects.update_or_create(
                            indicator=indicator,
                            country=country,
                            year=YEAR,
                            defaults={'value': value}
                        )

                        total_processed += 1
                        if created_dp:
                            total_created += 1
                        else:
                            total_updated += 1

                        if total_processed % 10 == 0:
                            self.stdout.write(f'Обработано: {total_processed}...')

                    if total_processed > 0:
                        break  # если что-то нашлось — выходим

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ Файл {csv_file} не найден!'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка чтения файла: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('\n✅ Импорт завершён!'))
        self.stdout.write(f'Обработано записей: {total_processed}')
        self.stdout.write(self.style.SUCCESS(f'Создано DataPoint: {total_created}'))
        self.stdout.write(self.style.SUCCESS(f'Обновлено DataPoint: {total_updated}'))
        self.stdout.write(f'Пропущено: {skipped}')
        self.stdout.write(self.style.SUCCESS(f'Ключ в latest_metrics: health_index_{YEAR}'))