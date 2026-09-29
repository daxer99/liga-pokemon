from django import forms

from .models import Temporada, Torneo


class ImportarTDFForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo .tdf",
        help_text="El archivo de resultados que exporta TOM al terminar el torneo.",
    )
    tipo = forms.ChoiceField(label="Tipo de torneo", choices=Torneo.Tipo.choices)
    temporada = forms.ModelChoiceField(
        label="Suma a la liga",
        queryset=Temporada.objects.all(),
        required=False,
        empty_label="No suma a ninguna liga",
    )
    reemplazar = forms.BooleanField(
        label="Reemplazar si ya estaba cargado",
        required=False,
        help_text="Útil si corregiste resultados en TOM y volviste a exportar.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        activa = Temporada.objects.filter(activa=True).first()
        if activa:
            self.fields["temporada"].initial = activa

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(".tdf"):
            raise forms.ValidationError("El archivo tiene que tener extensión .tdf.")
        if archivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo es demasiado grande para ser un .tdf.")
        return archivo
