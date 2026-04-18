import csv
import pycountry
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from ...models import Country, Indicator, IndicatorCategory, DataPoint


class Command(BaseCommand):
    help = 'Импорт Working hours per worker — name_ru НЕ трогается (русские названия сохраняются)'

    def get_alpha2_from_name(self, entity_name):
        """Поиск ISO alpha2 по названию страны (name, common_name, official_name)"""
        if not entity_name or entity_name.strip() in ('', '??'):
            return None
        name = entity_name.strip()
        try:
            # Быстрый поиск
            for attr in ['name', 'common_name', 'official_name']:
                try:
                    country = pycountry.countries.get(**{attr: name})
                    if country:
                        return country.alpha_2
                except LookupError:
                    pass

            # Полный перебор (на случай вариаций названий)
            for c in list(pycountry.countries):
                for attr in ['name', 'common_name', 'official_name']:
                    if hasattr(c, attr):
                        val = getattr(c, attr)
                        if val and val.lower() == name.lower():
                            return c.alpha_2
            return None
        except Exception:
            return None

    def handle(self, *args, **options):
        csv_file = 'working_hours_per_worker.csv'

        # === 1. Показатель ===
        category, _ = IndicatorCategory.objects.get_or_create(
            name='Труд', slug='labor'
        )

        indicator, created = Indicator.objects.get_or_create(
            code='working_hours_per_worker',
            defaults={
                'name': 'Рабочие часы на одного работника',
                'category': category,
                'unit': 'часов',
                'source': 'World Bank / ILO',
                'higher_better': False,   # меньше часов = лучше (баланс работы и жизни)
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Создан показатель: {indicator.name}'))

        # === 2. Подтверждение ===
        self.stdout.write(self.style.WARNING(f'\nФайл: {csv_file}'))
        self.stdout.write(self.style.WARNING('name_ru НЕ будет удалён — русские названия сохраняются!'))
        if input('Продолжить? (y/n): ').lower() != 'y':
            self.stdout.write(self.style.ERROR('Отменено.'))
            return

        # === 3. Импорт ===
        try:
            with open(csv_file, encoding='cp1251', errors='ignore', newline='') as f:
                reader = csv.reader(f, delimiter=';')
                header = next(reader, None)
                if not header:
                    self.stdout.write(self.style.ERROR('Файл пустой.'))
                    return

                self.stdout.write(self.style.SUCCESS(f'Заголовок: {header}'))
                self.stdout.write('Импорт...\n')

                total_processed = total_created = total_updated = skipped = 0

                for row in reader:
                    if len(row) < 3:
                        skipped += 1
                        continue

                    entity = row[0].strip().replace('"', '')
                    year_raw = row[1].strip()
                    val_raw = row[2].strip().replace('"', '')

                    if not entity or not year_raw:
                        skipped += 1
                        continue

                    try:
                        year = int(year_raw)
                        value = float(val_raw.replace(',', '.')) if val_raw not in ('', 'n/a', 'no data', '..', 'null') else None
                    except:
                        skipped += 1
                        continue

                    if value is None:
                        skipped += 1
                        continue

                    iso = self.get_alpha2_from_name(entity)
                    if not iso:
                        self.stdout.write(self.style.WARNING(f'⚠️ Нет ISO для {entity}'))
                        skipped += 1
                        continue

                    # ← ГЛАВНОЕ ИСПРАВЛЕНИЕ:
                    # name_ru НЕ трогаем вообще!
                    country, created_country = Country.objects.get_or_create(
                        iso_code=iso.lower(),
                        defaults={
                            'name': entity,
                            'slug': slugify(entity),
                            # name_ru намеренно НЕ указываем → остаётся как было
                        }
                    )

                    if not created_country:
                        # Обновляем только английское имя и slug, если страна уже была
                        country.name = entity
                        country.slug = slugify(entity)
                        country.save(update_fields=['name', 'slug'])

                    dp, created_dp = DataPoint.objects.update_or_create(
                        indicator=indicator,
                        country=country,
                        year=year,
                        defaults={'value': value}
                    )

                    total_processed += 1
                    if created_dp:
                        total_created += 1
                    else:
                        total_updated += 1

                    if total_processed % 20 == 0:
                        self.stdout.write(f'Обработано: {total_processed}...')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ {csv_file} не найден!'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('\n✅ Импорт завершён!'))
        self.stdout.write(f'Обработано: {total_processed}')
        self.stdout.write(self.style.SUCCESS(f'Создано DataPoint: {total_created}'))
        self.stdout.write(self.style.SUCCESS(f'Обновлено DataPoint: {total_updated}'))
        self.stdout.write(f'Пропущено: {skipped}')
        self.stdout.write(self.style.SUCCESS('Русские названия стран остались нетронутыми!'))