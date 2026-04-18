import pandas as pd
import xlrd  # обязательно импортируем

# Путь к файлу — замени на реальный!
file_path = 'C:/Users/sereg/Desktop/Таблицы для liveindex/imf-dm-export-20260203.xls'  # пример, укажи свой
sheet_name = 'PPPPC'  # или имя твоего листа

# Открываем workbook с флагом игнорирования ошибок
workbook = xlrd.open_workbook(file_path, ignore_workbook_corruption=True, on_demand=True)

# Читаем в pandas (попробуй header=0 или 1, если структура с заголовками в 2-й строке)
df = pd.read_excel(workbook, sheet_name=sheet_name, header=0)  # header=0 — первая строка как заголовки

# Для отладки: выведем столбцы и первые строки, чтобы понять структуру (раскомментируй при запуске)
# print("Столбцы:", df.columns.tolist())
# print(df.head(5))

# Страны: используй правильный заголовок (твой длинный — вероятно, это он; если нет, измени на df.iloc[:, 0])
countries = df['GDP per capita, current prices (Purchasing power parity; international dollars per capita)'].str.lower().str.strip()

# Значения: найди столбец, содержащий '2025' в имени (на случай '2025 estimate' или подобного)
year_columns = [col for col in df.columns if '2025' in str(col)]
if not year_columns:
    raise ValueError("Не найден столбец с '2025'! Проверь df.columns")
year_column = year_columns[0]  # Берём первый подходящий
values = df[year_column]

gdp_dict = {}
for country, value in zip(countries, values):
    if pd.notna(value) and pd.notna(country):
        try:
            gdp_dict[country] = int(float(value))  # на случай если значение float или строка
        except (ValueError, TypeError):
            pass  # пропустим некорректные строки

# Вывод JS
print('const gdpData = {')
for country, value in gdp_dict.items():
    print(f"  '{country}': {value},")
print('};')