from dal import autocomplete
from django.db.models import Q
from .models import District

class DistrictAutocomplete(autocomplete.Select2QuerySetView):
    """
    Возвращает список районов отфильтрованных по выбранному региону.
    DAL сам передаст значение поля 'region' через forward=['region'].
    """
    def get_queryset(self):
        qs = District.objects.all()

        # фильтр по выбранному блоку (приходит в forwarded)
        region_id = self.forwarded.get('region')
        if region_id:
            qs = qs.filter(region_id=region_id)

        # поиск по тексту
        if self.q:
            qs = qs.filter(
                Q(name_ru__icontains=self.q) |
                Q(name_uz__icontains=self.q)
            )

        return qs.order_by("code", "id")