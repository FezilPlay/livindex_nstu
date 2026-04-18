import csv
import pycountry
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from ...models import Country, Indicator, IndicatorCategory, DataPoint


class Command(BaseCommand):
    help = 'Импорт Life expectancy — name_ru НЕ трогается (русские названия сохраняются)'

    def get_alpha2(self, alpha3):
        if not alpha3 or alpha3.strip() in ('', '??'):
            return None
        try:
            return pycountry.countries.get(alpha_3=alpha3.strip().upper()).alpha_2
        except Exception:
            return None

    def handle(self, *args, **options):
        csv_file = 'life_expectancy.csv'

        # === 1. Показатель ===
        category, _ = IndicatorCategory.objects.get_or_create(
            name='Демография', slug='demography'
        )

        indicator, created = Indicator.objects.get_or_create(
            code='life_expectancy',
            defaults={
                'name': 'Ожидаемая продолжительность жизни при рождении',
                'category': category,
                'unit': 'лет',
                'source': 'World Bank / UN',
                'higher_better': True,
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
                    if len(row) < 4:
                        skipped += 1
                        continue

                    entity = row[0].strip().replace('"', '')
                    alpha3 = row[1].strip().replace('"', '')
                    year_raw = row[2].strip()
                    val_raw = row[3].strip().replace('"', '')

                    if not entity or not alpha3 or not year_raw:
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

                    iso = self.get_alpha2(alpha3)
                    if not iso:
                        self.stdout.write(self.style.WARNING(f'⚠️ Нет ISO для {entity} ({alpha3})'))
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