from kivymd.app import MDApp
from kivymd.uix.menu import MDDropdownMenu

from kivy.properties import StringProperty
from kivy.lang import Builder

KV = """
Screen:
    MDTextField:
        id: fahrenheit
        hint_text:"Enter Fahrenheit"
        helper_text: "Once you enter the fahrenheit the press submit"
        helper_text_mode: "on_focus"
        icon_right: "temperature-fahrenheit"
        pos_hint: {'center_x': 0.5, 'center_y': 0.9}
        size: 200, 25
        size_hint: None, None

    MDRoundFlatButton:
        text: "Enter"
        pos_hint: {'center': (0.5,0.2)}
        text_color: 0, 1, 0, 1
        size_hint: 0.25, 0.20
        on_release: app.show_data()

    MDLabel:
        id: label
        text: "Choice Result"
        pos_hint: {'center': (0.5,0.4)}
        text_color: 0, 0, 0, 1
        size_hint: 0.25, 0.20

    MDIconButton:
        id: button
        icon: "language-python"
        pos_hint: {"center_x": .5, "center_y": .5}
        on_release: app.dropdown1.open()
"""


class DemoApp(MDApp):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.screen = Builder.load_string(KV)

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": "Option1",
                "on_release": lambda *args: self.callback(self, "option1")
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Option2",
                "on_release": lambda *args: self.callback(self, "option2")
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Option3",
                "on_release": lambda *args: self.callback(self, "option3")
            }
        ]

        self.dropdown1 = MDDropdownMenu(items=menu_items, width_mult=4, caller=self.screen.ids.button)

    def build(self):
        return self.screen

    def show_data(self):
        input_fahrenheit = self.root.ids.fahrenheit.text
        print(input_fahrenheit)

    @staticmethod
    def callback(self, option):
        print("cookies")
        self.root.ids.label.text = option


DemoApp().run()