import os
import sys
import arcpy
import pythonaddins as pa

class Button1(object):
    """Implementation for Addin_addin.button_1 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        print('UTTLMaker')
        pa.GPToolDialog('UTTLMaker','PreArcHidro')

class Button2(object):
    """Implementation for Addin_addin.button_2 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pa.GPToolDialog('UTTLMaker','NodosHidro')

class Button3(object):
    """Implementation for Addin_addin.button_3 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pa.GPToolDialog('UTTLMaker','Nodostopograficos')

class Button4(object):
    """Implementation for Addin_addin.button_4 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pa.GPToolDialog('UTTLMaker','BatchPoints')

class ButtonClass5(object):
    """Implementation for Addin_addin.button_5 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pa.GPToolDialog('UTTLMaker','Segmentacion')

class ButtonClass6(object):
    """Implementation for Addin_addin.button_6 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        pa.GPToolDialog('UTTLMaker','GeneralSegmentacion')