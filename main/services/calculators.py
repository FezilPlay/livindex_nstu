from django.db.models import Q
from ..models import DataPoint, Country, City  # Добавь Country и City сюда!

class liveindexCalculator:
    @staticmethod
    def salary_minus_rent(obj, year=2026):
        """Расчёт: средняя зарплата - средняя аренда (для страны или города)"""
        salary_dp = DataPoint.objects.filter(
            indicator__code='average_salary',  # Замени на свой код индикатора
            year=year
        ).filter(
            Q(country=obj) if isinstance(obj, Country) else Q(city=obj)
        ).first()
        rent_dp = DataPoint.objects.filter(
            indicator__code='rent_1bed_city_center',
            year=year
        ).filter(
            Q(country=obj) if isinstance(obj, Country) else Q(city=obj)
        ).first()

        if salary_dp and rent_dp and salary_dp.value and rent_dp.value:
            return salary_dp.value - rent_dp.value
        return None

    @staticmethod
    def quality_of_life_index(obj, year=2026):
        """Композитный индекс качества жизни (пример с весами)"""
        weights = {
            'gini_index': -0.2,  # Неравенство (ниже — лучше)
            'average_salary': 0.3,
            'rent_index': -0.15,
            'safety_index': 0.2,
            'health_care_index': 0.1,
            # Добавь другие показатели из твоих Excel/Numbeo
        }
        score = 0
        for code, weight in weights.items():
            dp = DataPoint.objects.filter(
                indicator__code=code,
                year=year
            ).filter(
                Q(country=obj) if isinstance(obj, Country) else Q(city=obj)
            ).first()
            if dp and dp.value:
                value = dp.value
                if weight < 0:  # Инвертируем негативные
                    value = 100 - value  # Предполагаем шкалу 0-100
                score += value * abs(weight)
        return round(score, 2) if score else None