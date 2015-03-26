from langtools import _

import json
from kivy.logger import Logger
from ui.peachy_settings import SettingString, SettingNumeric, SettingBoolean

try:
    from VERSION import version, revision
except:
    version = "DEV"
    revision = "DEV"


class SettingsMapper(object):
    def __init__(self, api):
        self.api = api
        self.configuration_api = self.api.get_configuration_api()

    @property
    def config_info(self):
        return [
                {
                    'type': 'string',
                    'section': 'Info',
                    'desc': _('info.version_number DESCRIPTION'),
                    'title': _('info.version_number TITLE'),
                    'key': 'info.version_number',
                    'disabled': True
                },
                {
                    'type': 'string',
                    'section': 'Info',
                    'desc': _('info.serial_number DESCRIPTION'),
                    'title': _('info.serial_number TITLE'),
                    'key': 'info.serial_number',
                    'disabled': True
                },
                {
                    'type': 'string',
                    'section': 'Info',
                    'desc': _('info.hardware_version_number DESCRIPTION'),
                    'title': _('info.hardware_version_number TITLE'),
                    'key': 'info.hardware_version_number',
                    'disabled': True
                },
                {
                    'type': 'string',
                    'section': 'Info',
                    'desc': _('info.firmwware_version_number DESCRIPTION'),
                    'title': _('info.firmwware_version_number TITLE'),
                    'key': 'info.firmwware_version_number',
                    'disabled': True
                },
               ]

    @property
    def config_options(self):
        return [
                {
                    'type': 'bool',
                    'section': 'Options',
                    'key': 'options.use_sublayers',
                    'title': _('options.use_sublayers TITLE'),
                    'desc': _('options.use_sublayers DESCRIPTION'),
                    'values': [True, False]
                },
                {
                    'type': 'numeric',
                    'section': 'Options',
                    'key': 'options.sublayer_height_mm',
                    'title': _('options.sublayer_height_mm TITLE'),
                    'desc': _('options.sublayer_height_mm DESCRIPTION'),
                    'value_range': [0, None],
                    'ok_button_text': _("Ok"),
                    'cancel_button_text': _("Cancel")
                },
                {
                    'type': 'numeric',
                    'section': 'Options',
                    'key': 'options.laser_thickness_mm',
                    'title': _('options.laser_thickness_mm TITLE'),
                    'desc': _('options.laser_thickness_mm DESCRIPTION'),
                    'value_range': [0, None]
                },
                {
                    'type': 'numeric',
                    'section': 'Options',
                    'key': 'options.scaling_factor',
                    'title': _('options.scaling_factor TITLE'),
                    'desc': _('options.scaling_factor DESCRIPTION'),
                    'value_range': [0, None],
                    'ok_button_text': _("Ok"),
                    'cancel_button_text': _("Cancel")
                },
                {
                    'type': 'numeric',
                    'section': 'Options',
                    'key': 'options.overlap_amount_mm',
                    'title': _('options.overlap_amount_mm TITLE'),
                    'desc': _('options.overlap_amount_mm DESCRIPTION'),
                    'value_range': [0, None],
                    'ok_button_text': _("Ok"),
                    'cancel_button_text': _("Cancel")
                },
                {
                    'type': 'bool',
                    'values': [True, False],
                    'section': 'Options',
                    'key': 'options.use_shufflelayers',
                    'title': _('options.use_shufflelayers TITLE'),
                    'desc': _('options.use_shufflelayers DESCRIPTION'),
                },
                {
                    'type': 'bool',
                    'values': [True, False],
                    'section': 'Options',
                    'key': 'options.use_overlap',
                    'title': _('options.use_overlap TITLE'),
                    'desc': _('options.use_overlap DESCRIPTION'),
                },
                {
                    'type': 'numeric',
                    'section': 'Options',
                    'key': 'options.print_queue_delay',
                    'title': _('options.print_queue_delay TITLE'),
                    'desc': _('options.print_queue_delay DESCRIPTION'),
                    'value_range': [0, None],
                    'ok_button_text': _("Ok"),
                    'cancel_button_text': _("Cancel")
                },
                {
                    'type': 'numeric',
                    'section': 'Options',
                    'key': 'options.pre_layer_delay',
                    'title': _('options.pre_layer_delay TITLE'),
                    'desc': _('options.pre_layer_delay DESCRIPTION'),
                    'value_range': [0, None],
                    'ok_button_text': _("Ok"),
                    'cancel_button_text': _("Cancel")
                },]

    @property
    def section_map(self):
        return {
            _('Info'): self.config_info,
            _('Options'): self.config_options,

        }




    def refresh_settings(self, settings, config):
        settings.register_type('string', SettingString)
        settings.register_type('bool', SettingBoolean)
        settings.register_type('numeric', SettingNumeric)
        for (section, data) in self.section_map.items():
            settings.add_json_panel(section, config, data=json.dumps(data))

    def set_defaults(self, config):
        Logger.info("Setting Defaults")

    def _convert(self, entry_type, value):
        if entry_type == 'string':
            return value
        if entry_type == 'numeric':
            if '.' in value:
                return float(value)
            else:
                return int(value)
        if entry_type == 'bool':
            return value

    def update_setting(self, section, key, value):
        Logger.info(u"Setting changed  %s, %s -> %s" % (section, key, value))
        entry_type = [entry['type'] for entry in self.section_map[section] if entry['key'] == key][0]
        Logger.info("Wass a %s" % entry_type)
        setter = key.split('.')[1]
        getattr(self.configuration_api, 'set_' + setter)(self._convert(entry_type, value))

    def load_config(self, config):
        Logger.info("Loading Configs")
        self.configuration_api.load_printer(self.configuration_api.get_available_printers()[0])
        info_items = {
            'info.version_number': '%s, build %s' % (version, revision),
            'info.serial_number': 'Not Yet Determined',
            'info.hardware_version_number': 'Not Yet Determined',
            'info.firmwware_version_number': 'Not Yet Determined',
            }

        config_items = {}
        for item in self.config_options:
            key = item['key']
            getter = 'get_' + key.split('.')[1]
            config_items[key] = getattr(self.configuration_api, getter)()

        self.setall(config, 'Info', info_items)
        self.setall(config, 'Options', config_items)

    def setall(self, config, section, items):
        config.add_section(section)
        for (key, value) in items.items():
            config.set(section, key, value)
