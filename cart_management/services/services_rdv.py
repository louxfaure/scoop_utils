from datetime import datetime, time,timedelta
from ..models import Appointment,Person 
import pytz

class Resas(object):
    """Retourne les jours ouvrés dans la période [date_from:date_to]
    :param date_from: Date de début de la période
    :param date_to: Date de fin de la période
    :return: Générateur
    """
    def __init__(self,pickup_loc,hour_from,hour_to,plots_number,handling_time,days_for_booking,view_type='public'):

        self.list_days = []
        self.view_type=view_type
        self.pickup_loc = pickup_loc
        self.hour_from = hour_from
        self.hour_to = hour_to
        self.plots_number = plots_number
        self.handling_time = handling_time
        date_from = self.get_date_from()
        date_to = date_from + timedelta(days=days_for_booking)
        self.rdvs = self.get_appointments(date_from,date_to)       
        while date_from <= date_to:
            # Un jour est ouvré s'il n'est ni férié, ni samedi, ni dimanche
            if not self.is_holiday(date_from) and date_from.isoweekday() not in [6, 7]:
                # my_object = {date_from : my_hours}
                self.list_days.append(date_from)
            date_from += timedelta(days=1)
        print(self.rdvs)

    def get_date_from(self):
        now = datetime.today()
        # start_date = now.replace(hour=0, minute=0, second=0, microsecond=0,tzinfo=pytz.timezone('Europe/Paris'))
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date.isoweekday in [1,2,3,7]:
            return start_date + timedelta(days=self.handling_time)
        elif start_date.isoweekday in [4,5]:
            return start_date + timedelta(days=self.handling_time + 2)
        else :
             return start_date + timedelta(days=self.handling_time + 1)
        return start_date
    
    def easter_date(self,year):
        """
        Calcule la date du jour de Pâques d'une année donnée
        Voir https://github.com/dateutil/dateutil/blob/master/dateutil/easter.py
        
        :return: datetime
        """
        a = year // 100
        b = year % 100
        c = (3 * (a + 25)) // 4
        d = (3 * (a + 25)) % 4
        e = (8 * (a + 11)) // 25
        f = (5 * a + b) % 19
        g = (19 * f + c - e) % 30
        h = (f + 11 * g) // 319
        j = (60 * (5 - d) + b) // 4
        k = (60 * (5 - d) + b) % 4
        m = (2 * j - k - g + h) % 7
        n = (g - h + m + 114) // 31
        p = (g - h + m + 114) % 31
        day = p + 1
        month = n
        return datetime(year, month, day)


    def is_holiday(self,the_date):
        """
        Vérifie si la date donnée est un jour férié
        :param the_date: datetime
        :return: bool
        """
        year = the_date.year
        easter = self.easter_date(year)
        days = [
            datetime(year, 1, 1),  # Premier de l'an
            easter + timedelta(days=1),  # Lundi de Pâques
            datetime(year, 5, 1),  # Fête du Travail
            datetime(year, 5, 8),  # Victoire de 1945
            easter + timedelta(days=39),  # Ascension
            easter + timedelta(days=49),  # Pentecôte
            datetime(year, 7, 14),  # Fête Nationale
            datetime(year, 8, 15),  # Assomption
            datetime(year, 11, 1),  # Toussaint
            datetime(year, 11, 11),  # Armistice 1918
            datetime(year, 12, 25),  # Noël
        ]
        return the_date in days
    
    def get_appointments(self,date_from,date_to):
        list_rdv =  Appointment.objects.filter(library__exact=self.pickup_loc).filter(date__gte=date_from).exclude(date__gt=date_to + timedelta(days=1)).values_list('date', flat=True)
        return list_rdv

    def get_list_hours_for_public_view(self):
        list_hours =[]
        slot_length = 60//self.plots_number
        start_hour = self.hour_from
        end_hour = self.hour_to
        while start_hour <= end_hour:
            # print(start_hour)
            x = 0
            for plot in range(self.plots_number):
                plot = []
                for day in self.list_days:
                    hour = day + timedelta(hours=start_hour,minutes=x)
                    if hour in self.rdvs:
                            plot.append("-")
                    else:
                        plot.append(hour)
                x += slot_length
                list_hours.append(plot)
            start_hour += 1
        return list_hours

    def get_list_hours_for_admin_view(self):
        list_hours =[]
        slot_length = 60//self.plots_number
        start_hour = self.hour_from
        end_hour = self.hour_to
        while start_hour <= end_hour:
            # print(start_hour)
            x = 0
            for plot in range(self.plots_number):
                plot = []
                plot.append("{}H{}".format(start_hour,x))
                for day in self.list_days:
                    hour = day + timedelta(hours=start_hour,minutes=x)
                    if hour in self.rdvs:
                            appointment = Appointment.objects.get(library=self.pickup_loc,date=hour)
                            # person = Person.objects.get(id_alma=appointment.person)
                            person = appointment.person
                            plot.append(person.full_name)
                    else:
                        plot.append("-")
                x += slot_length
                list_hours.append(plot)
            start_hour += 1
        return list_hours
