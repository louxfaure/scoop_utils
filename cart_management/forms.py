from django import forms
from .models import PickupLocation

class NameForm(forms.Form):
    id_lecteur = forms.CharField(label='Identifiant du lecteur', max_length=100)
    library = forms.ModelChoiceField(label='Bibliothèque',queryset=PickupLocation.objects.all(), required=True)
        # date_rdv = forms.DateTimeField(label='Date', required=True)

    def clean(self): 
         # data from the form is fetched using super function 
        super(PostForm, self).clean() 
        username = self.cleaned_data.get('id_lecteur') 
        # conditions to be met for the username length 
        if len(username) < 5: 
            self._errors['username'] = self.error_class([ 
                'Minimum 5 characters required']) 
        if len(text) <10: 
            self._errors['username'] = self.error_class([ 
                'Post Should Contain a minimum of 10 characters']) 
  
        # return any errors if found 
        return self.cleaned_data 
