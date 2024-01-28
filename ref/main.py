from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.uix.vkeyboard import VKeyboard
# from kivymd.uix.screenmanager import MDScreenManager
# from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivy.config import Config
import numpy as np
Config.set('kivy', 'keyboard_mode', 'dock')

class MainApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.textfields = np.arange(0,6)

        self.scroll_layout = MDScrollView(id='layout_textfields')
        self.layout = MDGridLayout(cols=1)
        self.textfield = MDTextField(input_type='number',
                                     input_filter='float',
                                     on_click=self.focus)

        keyboard = VKeyboard(on_key_up = self.key_up)
        # keyboard.docked = True
        # keyboard.setup_mode()

        for t in self.textfields :
            print(t)
            self.layout.add_widget(
                MDGridLayout(
                    MDLabel(
                        text = f'label no:{t}'
                    ),
                    MDTextField(
                        id= f'textfield{t}',
                        hint_text = f'textfield no:{t}',
                        on_focus = lambda t: self.focus(t)
                    ),
                    cols=2,
                    padding= 20,
                    size_hint_y= None,
                    # height= minimum_height,
                    # width= minimum_width
                )
            )

        self.layout.add_widget(self.textfield)
        self.layout.add_widget(keyboard)
        # self.scroll_layout.add_widget(self.layout)

        # self.scroll_layout.add_widget(self.layout)
    
        return self.layout
    
    def focus(self):
        self.textfield.text = ""
    
    def key_up(self, keyboard, keycode, *args):
        if isinstance(keycode, tuple):
            print(keycode)
            keycode = keycode[1]

        prev_text = self.textfield.text

        self.textfield.text = f'{prev_text}{keycode}'

if __name__ == '__main__':
    MainApp().run()