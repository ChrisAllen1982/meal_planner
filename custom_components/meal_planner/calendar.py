"""Support for Meal_Planner Calendar."""
import copy
import logging
import calendar
import pypandoc

from datetime import date, datetime, timedelta, time

import arrow

import uuid

import voluptuous as vol
from homeassistant.components.calendar import (ENTITY_ID_FORMAT,
                                               PLATFORM_SCHEMA,
                                               CalendarEventDevice,
                                               calculate_offset,
                                               is_offset_reached)
from homeassistant.const import CONF_NAME, CONF_PATH
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import generate_entity_id

import zipfile
import xml.etree.ElementTree as ET
import random
import json

VERSION = "1.0.0"

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE_ID = 'device_id'
CONF_MEALS = 'meals'
CONF_START_TIME = 'start_time'
CONF_END_TIME = 'end_time'
CONF_FILTER = 'filter'
CONF_RESET_DAY = 'reset_day'
JSON_CACHE = 'meal_plan.json'


STORAGE_KEY = "meal_planner.storage"
STORAGE_VERSION = 1

OFFSET = "!!"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        # pylint: disable=no-value-for-parameter
        vol.Required(CONF_PATH): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_RESET_DAY): cv.string,
        vol.Optional(CONF_MEALS, default=[]):
        vol.All(cv.ensure_list, vol.Schema([
            vol.Schema({
                vol.Optional(CONF_FILTER, None): cv.string,
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_START_TIME): cv.string,
                vol.Optional(CONF_END_TIME, None): cv.string
            })
        ]))
    }
)


MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=15)


def setup_platform(hass, config, add_entities, _=None):
    """Set up the Meal_Planner Calendar platform """
    _LOGGER.debug("Setting up meal_planner calendars")
    calendar_devices = []

    meals = {}

    for meal in config.get(CONF_MEALS):
        meal_name = meal.get(CONF_NAME)

        item = {
            CONF_START_TIME : meal.get(CONF_START_TIME),
            CONF_END_TIME : meal.get(CONF_END_TIME) or meal.get(CONF_START_TIME),
            CONF_FILTER : meal.get(CONF_FILTER)
        }

        meals[meal_name] = item

    device_data = {
        CONF_NAME: config.get(CONF_NAME),
        CONF_PATH: config.get(CONF_PATH),
        CONF_RESET_DAY: config.get(CONF_RESET_DAY),
        CONF_MEALS: meals
    }
    device_id = "{}".format(device_data[CONF_NAME])
    entity_id = generate_entity_id(ENTITY_ID_FORMAT, device_id, hass=hass)
    calendar_devices.append(
        MealPlannerEventDevice(entity_id, device_data))

    add_entities(calendar_devices)


class Recipe:

    @property
    def title(self):
        raise NotImplementedError

    @property
    def category(self):
        raise NotImplementedError

    @property
    def ingredients_list(self):
        raise NotImplementedError

    @property
    def instructions(self):
        raise NotImplementedError

    @property
    def description(self):
        raise NotImplementedError

    @property
    def image(self):
        raise NotImplementedError

    def __str__(self):

        strings = ["# %s" % self.title]

        if self.description is not None:
            strings.append("_%s_" % self.description)

        strings.append('\n')

        if self.image is not None:
            strings.append("![image](%s)" % self.image)

        strings.append('\n')
        for ingredient in self.ingredients_list:
            strings.append("* %s" % ingredient)

        strings.append('\n')

        for instruction in self.instructions:
            strings.append("1. %s" % instruction)

        return '\n'.join(strings)




class McbRecipe(Recipe):
    def __init__(self, obj):
        self.object = obj

    @property
    def title(self):
        return self.object.find('title').text

    @property
    def category(self):
        category = self.object.find('category')

        if category is not None:
            return category.text

        return 'None'

    @property
    def ingredients_list(self):
        ret_item = []
        ingredients = self.object.find('ingredient')
        for item in ingredients.iter('li'):
            ret_item.append(item.text)

        return ret_item

    @property
    def instructions(self):
        ret_item = []
        instructions = self.object.find('recipetext')
        for item in instructions.iter('li'):
            if item.text is not None:
                ret_item.append(item.text)

        return ret_item

    @property
    def description(self):
        category = self.object.find('description')

        if category is not None:
            return category.text

        return None

    @property
    def image(self):
        image = self.object.find('imageurl')

        if image is not None:
            return image.text

        return None



class MCBParser:

    def __init__(self, file):
        archive = zipfile.ZipFile(file, 'r')
        xml_data = archive.read('my_cookbook.xml')
        self.recipeDictionary = {}


        root = ET.fromstring(xml_data)
        for recipe in root.iter('recipe'):
            recipeItem = McbRecipe(recipe)
            self.recipeDictionary[recipeItem.title] = recipeItem

    def recipies(self, filter=None):
        return list(self.recipeDictionary.keys())

    def recipeDetails(self, name):
        return self.recipeDictionary[name]





class MealPlannerEventDevice(CalendarEventDevice):

    def __init__(self, entity_id, device_data):
        _LOGGER.debug("Initializing calendar: %s", device_data[CONF_NAME])
        self.entity_id = entity_id
        self._event = None
        self._name = device_data[CONF_NAME]
        self._data = MCBParser(device_data[CONF_PATH])
        self._reset_day = device_data[CONF_RESET_DAY]

        self._meals = device_data[CONF_MEALS]

        #if self.planned_meals is None:
        self.planned_meals = {}

    @property
    def event(self):
        """Returns the current event for the calendar entity or None"""
        return self._event

    @property
    def name(self):
        """Returns the name of the calendar entity"""
        return self._name

    async def async_get_events(self, _, start_date, end_date):
        """Get all events in a specific time frame."""
        today = date.today()
        events = []

        

      #  with open('tmp.md', 'w') as mdfile:
      #      mdfile.write(recipeList.recipeDetails(self.planned_meals[today.isoformat()]).__str__())

        for item_date, meals in self.planned_meals.items():

            for meal, selection in meals.items():

                _LOGGER

                meal_details = self._meals[meal]

                details = self._data.recipeDetails(selection)

                start = time.fromisoformat(meal_details[CONF_START_TIME])
                end = time.fromisoformat(meal_details[CONF_END_TIME])

                data = {
                    'uid': uuid.uuid4().hex,
                    'title': selection,
                    'start': self.get_date_formatted(datetime.combine(date.fromisoformat(item_date), start), False),
                    'end':   self.get_date_formatted(datetime.combine(date.fromisoformat(item_date), end), False),
                    'location': '',
                    'description': details.__str__()
                }
                
                # Note that we return a formatted date for start and end here,
                # but a different format for self.event!
                events.append(data)


        return events

    def plan_meals(self):
        
        meal_collecction = {}

        start_date = date.today()
        end = start_date + timedelta(days=7)
        tmp = start_date

        while tmp < end:

            meals = {}

            for meal_name, meal in self._meals.items():               

                _LOGGER.debug('Planning %s on %s', meal_name, tmp)

                meals[meal_name] = random.choice(self._data.recipies(meal[CONF_FILTER]))

            meal_collecction[tmp.isoformat()] = meals

            tmp = tmp + timedelta(days=1)  # replace the interval at will

            if calendar.day_name[tmp.weekday()] == self._reset_day:
                break


        return meal_collecction


    def update(self):
        """Update event data."""

        isotoday = date.today().isoformat()

        if isotoday not in self.planned_meals:
            _LOGGER.info('Planning meals from %s', isotoday)
            self.planned_meals.clear()
            self.planned_meals = self.plan_meals()
            _LOGGER.debug(self.planned_meals)

        data = None
        
        for isodate, meals in self.planned_meals.items():

            for meal, selection in self.planned_meals[isodate].items():
                
                meal_details = self._meals[meal]

                start = datetime.combine(date.fromisoformat(isodate), time.fromisoformat(meal_details[CONF_START_TIME]))
                end   = datetime.combine(date.fromisoformat(isodate), time.fromisoformat(meal_details[CONF_END_TIME]))

                details = self._data.recipeDetails(selection)

                if start > datetime.now() and data is None:

                    data = {
                        'summary': selection,
                        'start': self.get_hass_date(start, False),
                        'end': self.get_hass_date(end, False),
                        'location': '',
                        'description': details.__str__()
                    }

                    _LOGGER.debug('Setting current event: %s', selection)
                    self._event = data

                    output = pypandoc.convert_text(data['description'], 'html', format='md', outputfile="/home/homeassistant/.homeassistant/www/index.html", extra_args=['-s', '-c style.css'])

                    break
                

        return True
    
    @staticmethod
    def get_date_formatted(arw, is_all_day):
        """Return the formatted date"""
        # Note that all day events should have a time of 0, and the timezone
        # must be local.  The server probably has the timezone erroneously set
        # to UTC!
        arw = arrow.get(arw)

        if is_all_day:

            arw = arw.replace(hour=0, minute=0, second=0,
                              microsecond=0, tzinfo='local')
            return arw.format('YYYY-MM-DD')

        return arw.isoformat()

    @staticmethod
    def get_hass_date(arw, is_all_day):
        """Return the wrapped and formatted date"""
        if is_all_day:
            return {'date': MealPlannerEventDevice.get_date_formatted(arw, is_all_day)}
        return {'dateTime': MealPlannerEventDevice.get_date_formatted(arw, is_all_day)}









