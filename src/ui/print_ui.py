import datetime
import time

from kivy.uix.screenmanager import Screen
from kivy.graphics import *
from kivy.logger import Logger
from kivy.lang import Builder
from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.resources import resource_find
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.image import Image

from ui.custom_widgets import ErrorPopup, I18NPopup
from ui.peachy_widgets import LaserWarningPopup
from infrastructure.langtools import _

import os

Builder.load_file('ui/print_ui.kv')


class ListElement(BoxLayout):
    title = StringProperty()
    value = StringProperty()


class PrinterAnimation(RelativeLayout):
    padding = NumericProperty(40)

    printer_actual_dimensions = ListProperty([80, 80, 80])
    printer_current_actual_height = NumericProperty(0.0)

    printer_height = NumericProperty(1)
    printer_width = NumericProperty(1)
    printer_left = NumericProperty(0)
    printer_bottom = NumericProperty(40)

    laser_size = ListProperty([40, 40])

    resin_height = NumericProperty(20)
    water_height = NumericProperty(20)

    scale = NumericProperty(1.0)

    resin_color = ListProperty([0.0, 0.8, 0.0, 0.6])
    water_color = ListProperty([0.2, 0.2, 1.0, 0.6])
    container_color = ListProperty([1.0, 1.0, 1.0, 1.0])
    laser_color = ListProperty([0.0, 0.0, 1.0, 1.0])

    drip_history = ListProperty()
    laser_points = ListProperty()

    middle_x = NumericProperty(52)

    def __init__(self, **kwargs):
        super(PrinterAnimation, self).__init__(**kwargs)
        self.drip_time_range = 5
        self.images = []
        self.laser_pos = 60
        
        self.waiting_for_drips = True
        self._refresh_rate = App.get_running_app().refresh_rate
        self._laser_speed = 100.0 / (1.0 / self._refresh_rate)

    def on_size(self, *largs):
        bounds_y = (self.height * 0.7) - self.resin_height
        bounds_x = self.width - (self.padding * 2)
        printer_x = self.printer_actual_dimensions[0]
        printer_y = self.printer_actual_dimensions[1]

        self.scale = min(bounds_y / printer_y, bounds_x / printer_x)
        self.printer_width = printer_x * self.scale
        self.printer_height = printer_y * self.scale

    def redraw(self, key):
        self._draw_drips()
        self._draw_laser()
        Clock.unschedule(self.redraw)
        Clock.schedule_once(self.redraw, self._refresh_rate)

    def animation_stop(self):
        Clock.unschedule(self.redraw)
        self.laser_points = []
        while self.images:
            self.remove_widget(self.images.pop())

    def _draw_drips(self):
        pass
        # while self.images:
        #     self.remove_widget(self.images.pop())
        # top = time.time()
        # bottom = top - self.drip_time_range
        # for drip_time in self.drip_history:
        #     if drip_time > bottom:
        #         time_ago = top - drip_time
        #         y_pos_percent = (self.drip_time_range - time_ago) / self.drip_time_range
        #         drip_pos_y = (self.height * y_pos_percent) + self.padding
        #         image_widget = Image(source="resources/images/drop.png", size_hint=[None, None], size=[10, 10], pos=[self.printer_left + 20, drip_pos_y], allow_strech=True)
        #         self.images.append(image_widget)
        # for image in self.images:
        #     self.add_widget(image)

    def _draw_laser(self):
        if self.waiting_for_drips:
            self.laser_points = []
        else:
            if (self.laser_pos >= 100.0 - abs(self._laser_speed)) or (self.laser_pos <= abs(self._laser_speed)):
                self._laser_speed = self._laser_speed * -1
            self.laser_pos += self._laser_speed
            laser_x = self.printer_left + (self.printer_width * (self.laser_pos / 100.0))

            self.laser_points = [self.middle_x, self.height - self.padding,
                                 laser_x,          self.water_height + self.printer_bottom + self.resin_height]


class SettingsPopUp(I18NPopup):
    def add_setting(self, widget):
        self.ids.print_settings.add_widget(widget)

    def remove_settings(self):
        self.ids.print_settings.clear_widgets()


class PrintingUI(Screen):
    printer_actual_dimensions = ListProperty([10, 10, 10])

    status = StringProperty("Starting")
    model_height = NumericProperty(0.0)
    start_time = ObjectProperty(datetime.datetime.now())
    drips = NumericProperty(0)
    print_height = NumericProperty(0.0)
    drips_per_second = NumericProperty(0.0)
    errors = ListProperty()
    waiting_for_drips = StringProperty("Starting")
    elapsed_time = StringProperty("0")
    current_layer = NumericProperty(0)
    skipped_layers = NumericProperty(0)

    def __init__(self, api, **kwargs):
        self.return_to = 'mainui'
        super(PrintingUI, self).__init__(**kwargs)
        self.api = api
        self.print_api = None
        self.print_options = []
        self.settings_popup = SettingsPopUp()
        self.data = {}
        self._refresh_rate = App.get_running_app().refresh_rate

    def on_printer_dimensions(self, instance, value):
        self.ids.printer_animation.printer_actual_dimensions = value

    def on_model_height(self, instance, value):
        self.ids.printer_animation.printer_current_actual_height = value

    def time_delta_format(self, td):
        total_seconds = td.total_seconds()
        hours = int(total_seconds) / (60 * 60)
        remainder = int(total_seconds) % (60 * 60)
        minutes = remainder / 60
        return "{0}:{1:02d}".format(hours, minutes)

    def callback(self, data):
        self.data = data

    def _callback(self, arg):
        data = self.data
        if 'status' in data:
            self.status = data['status']
        if 'model_height' in data:
            self.model_height = data['model_height']
        if 'start_time' in data:
            self.start_time = data['start_time']
        if 'drips' in data:
            self.drips = data['drips']
        if 'height' in data:
            self.print_height = data['height']
        if 'drips_per_second' in data:
            self.drips_per_second = data['drips_per_second']
        if 'errors' in data:
            self.errors = data['errors']
        if 'waiting_for_drips' in data:
            self.ids.printer_animation.waiting_for_drips = data['waiting_for_drips']
            self.waiting_for_drips = str(data['waiting_for_drips'])
        if 'elapsed_time' in data:
            self.elapsed_time = self.time_delta_format(data['elapsed_time'])
        if 'current_layer' in data:
            self.current_layer = data['current_layer']
        if 'skipped_layers' in data:
            self.skipped_layers = data['skipped_layers']
        if 'drip_history' in data:
            self.ids.printer_animation.drip_history = data['drip_history']

        Clock.unschedule(self._callback)
        if self.status == 'Complete':
            self.ids.printer_animation.animation_stop()
            self.play_complete_sound()
            self.ids.navigate_button.text_source = _("Print Complete")
            self.ids.navigate_button.background_color = [0.0, 2.0, 0.0, 1.0]
            self._finished = True
        elif self.status == 'Failed':
            self.ids.printer_animation.animation_stop()
            self.play_failed_sound()
            self.ids.navigate_button.text_source = _("Print Failed")
            self.ids.navigate_button.background_color = [2.0, 0.0, 0.0, 1.0]
            self._finished = True
        else:
            Clock.schedule_once(self._callback, self._refresh_rate)

    def print_file(self, *args, **kwargs):
        self.print_options = [self._print_file, args, kwargs]
        popup = LaserWarningPopup(title=_('Laser Safety Notice'), size_hint=(0.6, 0.6))
        popup.bind(on_dismiss=self.is_safe)
        popup.open()

    def _print_file(self, filename, start_height=0.0, return_name='mainui', force_source_speed=False):
        self.return_to = return_name
        try:
            filepath = filename[0].encode('utf-8')
            self.print_api = self.api.get_print_api(start_height=start_height, status_call_back=self.callback)
            self.path = os.path.basename(filepath)
            self.print_api.print_gcode(filepath, force_source_speed=force_source_speed)
        except Exception as ex:
            popup = ErrorPopup(title='Error', text=str(ex), size_hint=(0.6, 0.6))
            popup.open()
            self.parent.current = self.return_to

    def is_safe(self, instance):
        if instance.is_safe():
            Clock.schedule_once(self.ids.printer_animation.redraw)
            Clock.schedule_once(self._callback, self._refresh_rate)
            self.print_options[0](*self.print_options[1], **self.print_options[2])
        else:
            self.parent.current = self.return_to

    def print_generator(self, *args, **kwargs):
        self.print_options = [self._print_generator, args, kwargs]
        popup = LaserWarningPopup()
        popup.bind(on_dismiss=self.is_safe)
        popup.open()

    def _print_generator(self, generator, return_name='mainui', force_source_speed=False):
        self.return_to = return_name
        try:
            self.print_api = self.api.get_print_api(status_call_back=self.callback)
            self.print_api.print_layers(generator, force_source_speed=force_source_speed)
        except Exception as ex:
            popup = ErrorPopup(title='Error', text=str(ex), size_hint=(0.6, 0.6))
            popup.open()
            self.parent.current = self.return_to

    def restart(self):
        self.ids.printer_animation.animation_stop()
        if self.print_api:
            self.print_api.close()
        self.print_api = None
        self.ids.navigate_button.text_source = _('Cancel Print')
        self.ids.navigate_button.background_color = [2.0, 1.0, 0.0, 1.0]
        last_print = App.get_running_app().last_print
        if last_print.print_type is "file":
            self.print_file(last_print.source, self.return_to)
        elif last_print.print_type is "test_print":
            generator = self.api.get_test_print_api().get_test_print(*last_print.source)
            self.print_generator(generator, self.return_to)
        else:
            raise("Unsupported Print Type %s" % last_print.print_type)

    def play_complete_sound(self):
        sound_file = resource_find("complete.wav")
        if sound_file:
            sound = SoundLoader.load(sound_file)
            if sound:
                sound.play()
        else:
            Logger.warning("Sound was unfound")

    def play_failed_sound(self):
        sound_file = resource_find("fail.wav")
        if sound_file:
            sound = SoundLoader.load(sound_file)
            if sound:
                sound.play()
        else:
            Logger.warning("Sound was unfound")

    def on_pre_enter(self):
        for (title, value) in self.parent.setting_translation.get_settings().items():
            self.settings_popup.add_setting(ListElement(title=title, value=value))
        self.ids.navigate_button.text_source = _('Cancel Print')
        self.ids.navigate_button.background_color = [2.0, 1.0, 0.0, 1.0]

    def on_pre_leave(self):
        Clock.unschedule(self._callback)
        if self.print_api:
            self.print_api.close()
        self.ids.printer_animation.animation_stop()
        self.print_api = None
        self.settings_popup.remove_settings()
