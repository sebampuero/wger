#  This file is part of wger Workout Manager <https://github.com/wger-project>.
#  Copyright (C) 2013 - 2021 wger Team
#
#  wger Workout Manager is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  wger Workout Manager is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Standard Library
import datetime
from typing import List

# Django
from django.db import models
from django.utils.translation import gettext_lazy as _

# wger
from wger.core.models import DaysOfWeek
from wger.manager.dataclasses import SlotData


class DayType(models.TextChoices):
    NORMAL = 'normal'
    EMOM = 'enom'
    AMRAP = 'amrap'
    HIIT = 'hiit'
    TABATA = 'tabata'
    EDT = 'edt'
    RFT = 'rft'
    AFAP = 'afap'


class DayNg(models.Model):
    """
    Model for a training day
    """

    routine = models.ForeignKey(
        'Routine',
        verbose_name=_('Routine'),
        on_delete=models.CASCADE,
        related_name='days',
    )

    next_day = models.ForeignKey(
        'self',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    type = models.CharField(
        choices=DayType.choices,
        max_length=10,
        default=DayType.NORMAL,
        null=False,
    )

    name = models.CharField(
        max_length=20,
        verbose_name=_('Description'),
    )

    description = models.CharField(
        max_length=250,
        verbose_name=_('Description'),
    )

    is_rest = models.BooleanField(
        default=False,
    )
    """
    Flag indicating that this day is a rest day.

    Rest days have no exercises
    """

    need_logs_to_advance = models.BooleanField(
        default=False,
    )
    """
    Needs logs to advance to the next day
    """

    last_day_in_week = models.BooleanField(
        default=False,
    )
    """
    Flag indicating that this is the last workout day in the week
    """

    def __str__(self):
        """
        Return a more human-readable representation
        """
        return self.description

    def get_owner_object(self):
        """
        Returns the object that has owner information
        """
        return self.routine

    def can_proceed(self, date: datetime.date) -> bool:
        """
        Checks whether the user can proceed to the next day in the sequence

        This is possible if
        - the day doesn't require logs
        - the day requires logs, and they exist
        - the date is in the future (used e.g. for calendars where we assume we will proceed)
        """
        if (
            not self.need_logs_to_advance
            or self.workoutsession_set.filter(date=date).exists()
            or date > datetime.date.today()
        ):
            return True

        return False

    def get_slots_gym_mode(self, iteration: int) -> List[SlotData]:
        """
        Return the sets for this day
        """
        return [
            SlotData(comment=s.comment, exercises=s.get_exercises(), sets=s.get_sets(iteration))
            for s in self.slots.all()
        ]

    def get_slots_display_mode(self, iteration: int) -> List[SlotData]:
        """
        Return the sets for this day.

        The difference to get_slots above is that here some data massaging happens
        so that we can better display the data in the template. Specially, we
        collect the sets for the same exercise in the same slot.

        This only happens for slots that have only one exercise.

        Instead of
        * Slot1 -> Exercise1, [Config1]
        * Slot2 -> Exercise1, [Config2]
        * Slot3 -> Exercise1, [Config3]

        We return
        * Slot1 -> Exercise1, [Config1, Config2, Config3]

        """
        out = []
        last_exercise_id = None
        current_slot = None
        for slot in self.slots.all():
            if slot.is_superset:
                out.append(
                    SlotData(
                        comment=slot.comment,
                        exercises=slot.get_exercises(),
                        sets=[s.data for s in slot.set_data(iteration)],
                    )
                )
                current_slot = None
            elif not slot.get_exercises():
                continue
            else:
                exercise_id = slot.get_exercises()[0]
                if exercise_id != last_exercise_id:
                    current_slot = SlotData(
                        comment=slot.comment,
                        exercises=[exercise_id],
                        sets=[s.data for s in slot.set_data(iteration)],
                    )
                    out.append(current_slot)
                    last_exercise_id = exercise_id
                else:
                    current_slot.sets.extend([s.data for s in slot.set_data(iteration)])

        return out


class Day(models.Model):
    """
    Model for a training day
    """

    training = models.ForeignKey(
        'Workout',
        verbose_name=_('Workout'),
        on_delete=models.CASCADE,
    )

    description = models.CharField(
        max_length=100,
        verbose_name=_('Description'),
        help_text=_(
            'A description of what is done on this day (e.g. '
            '"Pull day") or what body parts are trained (e.g. '
            '"Arms and abs")'
        ),
    )
    day = models.ManyToManyField(DaysOfWeek, verbose_name=_('Day'))

    def __str__(self):
        """
        Return a more human-readable representation
        """
        return self.description

    def get_owner_object(self):
        """
        Returns the object that has owner information
        """
        return self.training

    @property
    def days_txt(self):
        return ', '.join([str(_(i.day_of_week)) for i in self.day.all()])

    @property
    def get_first_day_id(self):
        """
        Return the PK of the first day of the week, this is used in the template
        to order the days in the template
        """
        return self.day.all()[0].pk
