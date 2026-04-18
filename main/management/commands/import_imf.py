import csv
import pycountry
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from ...models import Country, Indicator, IndicatorCategory, DataPoint


class Command(BaseCommand):
    help = 'Импорт ВВП (ППС) с заполнением name_ru'

    MANUAL_MAP = {
        'Russia': 'RU',
        'South Korea': 'KR',
        'Vietnam': 'VN',
        'Iran': 'IR',
        'Tanzania': 'TZ',
        'Bolivia': 'BO',
        'Venezuela': 'VE',
        'United Kingdom': 'GB',
        'United States': 'US',
        'Turkey': 'TR',
        'Czech Republic': 'CZ',
        'Kosovo': 'KO',
        'Taiwan Province of China': 'TW',
        'Hong Kong SAR': 'HK',
        'Macao SAR': 'MO',
        'Lao P.D.R.': 'LA',
        'Syria': 'SY',
        'Slovenia': 'SI',
        'Somalia': 'SO',
        'Democratic Republic of the Congo': 'CD',
        'China': 'CN',
        'Ivory Coast': 'CI',
        'Niger': 'NE',
        'Taiwan': 'TW',
        'Bahamas': 'BS',
    }

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def get_iso_code(self, name):
        name_clean = name.strip().replace('"', '')
        if name_clean in self.MANUAL_MAP:
            return self.MANUAL_MAP[name_clean]
        try:
            return pycountry.countries.search_fuzzy(name_clean)[0].alpha_2
        except Exception:
            return "??"

    def handle(self, *args, **options):
        category, _ = IndicatorCategory.objects.get_or_create(
            name='Экономика',
            slug='economy'
        )

        indicator, _ = Indicator.objects.get_or_create(
            code='gdp_ppp',
            defaults={
                'name': 'ВВП (ППС) на душу населения',
                'category': category,
                'unit': 'Int$',
                'source': 'IMF'
            }
        )

        self.stdout.write(self.style.WARNING("Очистка старых данных..."))
        DataPoint.objects.all().delete()
        Country.objects.all().delete()

        with open(options['csv_file'], encoding='cp1251', errors='ignore', newline='') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)

        if not rows:
            self.stdout.write(self.style.ERROR("Файл пустой."))
            return

        header = rows[0]

        year_columns = []
        for i, col in enumerate(header):
            clean = col.strip().replace('"', '').replace('.0', '')
            if clean.isdigit():
                year = int(clean)
                if 1980 <= year <= 2030:
                    year_columns.append((i, year))

        if not year_columns:
            self.stdout.write(self.style.ERROR("Не найдены колонки с годами."))
            self.stdout.write(f"Первая строка файла: {header}")
            return

        self.stdout.write(f"Найдено {len(year_columns)} колонок с годами.")

        total_created = 0

        for row in rows[2:]:  # 1-я строка заголовок, 2-я пустая
            if len(row) < 2:
                continue

            raw_name = row[0].strip().replace('"', '')
            raw_name_ru = row[1].strip().replace('"', '') if len(row) > 1 else ""

            if not raw_name:
                continue

            if any(x in raw_name for x in ['GDP', '©', 'IMF', 'Notes', 'World']):
                continue

            iso = self.get_iso_code(raw_name)
            if iso == "??":
                continue

            country, _ = Country.objects.update_or_create(
                iso_code=iso.lower(),
                defaults={
                    'name': raw_name,
                    'name_ru': raw_name_ru or None,
                    'slug': slugify(raw_name),
                }
            )

            datapoints_to_create = []
            for col_idx, year in year_columns:
                if col_idx >= len(row):
                    continue

                val_raw = row[col_idx].strip().replace('"', '')
                if val_raw in ['', 'n/a', 'no data', 'no-data', 'null', '..']:
                    continue

                try:
                    val = float(val_raw.replace(',', '.'))
                except ValueError:
                    continue

                datapoints_to_create.append(
                    DataPoint(
                        country=country,
                        indicator=indicator,
                        year=year,
                        value=val
                    )
                )

            if datapoints_to_create:
                DataPoint.objects.bulk_create(datapoints_to_create)
                total_created += len(datapoints_to_create)

            self.stdout.write(f"Загружено: {raw_name} ({iso})")

        self.stdout.write(self.style.SUCCESS(f"Готово. Добавлено {total_created} записей."))