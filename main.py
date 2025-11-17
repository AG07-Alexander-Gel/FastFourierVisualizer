import mp3
import pygame.mixer as pgm
import dearpygui.dearpygui as dpg
from tkinter import filedialog
from screeninfo import get_monitors
from enum import Enum
import numpy as np
import math
import gc

import time
import threading

def form_string(txt: str):
    new_txt = ""
    for c in txt[::-1]:
        if "/" not in c:
            new_txt += c
        else:
            break

    return new_txt[::-1].replace(".mp3","")

class UiButtonTags(Enum):
    RUN = 100
    STOP = 101
    SELECT = 102

class FINALhzText(Enum):
    Bass = "150"          #   (0          ,   281.25)
    Low = "450"           #   (328.125    ,   515.625)
    Mid = "1500"          #   (562.5      ,   2015.625)
    Upper = "3500"        #   (2062.5     ,   4031.25)
    Presence = "5000"     #   (4078.125   ,   6000.0)
    Inbet = "9000"        #   (6046.875   ,   13000.0)
    Treble = "15000"      #   (13046.875  ,   20015.625)
    HighP = "20000+"      #   (20062.5    ,   24000.0)     

class FINALhzRanges(Enum):
    Bass = 281.25 
    Low = 515.625
    Mid = 2015.625
    Upper = 4031.25
    Presence = 6000.0
    Inbet = 13000.0
    Treble = 20015.625
    HighP = 24000.0  


class Ticking:

    def __init__(self):
        self.maxTick = 1000000000

    def change_tick(self, val : int):
        self.maxTick = val
        
class MyFourier:

    def __init__(self, decoder, samples_window_size=1024):
        def to_mono(buf):
            return (np.frombuffer(buf, np.int16).reshape(-1, 2).sum(axis=1) // 2).astype(np.int16)
        
        self.SampleRate = decoder.get_sample_rate()

        self.TWindow = samples_window_size / self.SampleRate

        self.binSize = self.SampleRate / samples_window_size
        self.binAmount = samples_window_size / 2
        self.MaxFreq = self.SampleRate/2

        stereo_pcm = decoder.read()
        self.mono_pcm = to_mono(stereo_pcm)

        self.samplesSize = samples_window_size

        self.current = 0
        self.max = math.floor(len(self.mono_pcm)/self.samplesSize)        

        self.neoquist = int(self.samplesSize/2)+1
        self.bin_values = np.zeros((self.max,self.neoquist),dtype=np.uint16)

        self.hz_ranges = None

    def gen_hz_ranges(self,order : dict):
        keys = list(order.keys())
        values = list(order.values())

        for s in range(0,self.max):
            spec = self.bin_values[s]
            hzb = np.zeros(len(keys),dtype=np.uint32)

            hz = 0
            kv = 0
            for b in range(0,self.neoquist):
                
                if b*self.binSize <= values[kv]:
                    hz += int(spec[b])
                else:
                    hzb[kv] = hz
                    hz = 0
                    kv+=1
            self.hz_ranges[s] = hzb
        
        return np.max(self.hz_ranges)
        

    def gen(self, order : dict):
        while self.current < self.max:
            values = self.mono_pcm[(self.current*self.samplesSize) : ((self.current+1)*self.samplesSize)]
            hamming = np.hamming(self.samplesSize)
            values_to_window = values * hamming

            spectral_values = np.fft.fft(values_to_window)
        
            self.bin_values[self.current] = abs(spectral_values[:self.neoquist])
            self.current += 1
        
        self.hz_ranges = np.zeros((self.max,len(order.keys())),dtype=np.uint32)       
        return self.gen_hz_ranges(order=order)
            
        
    def print_info(self):
        print(f"TimeWindow: {str(self.TWindow*1000)[0:5]}ms ; Bin Size: {self.binSize} Hz ; Bin Amount: {self.binAmount} ; MaxFrequencyToCheck: {self.MaxFreq} Hz")

class FrequencyVisualizer:

    def select_file(self, sender, value, user_data):
        new_file = filedialog.askopenfilename()

        if ".mp3" in str(new_file):
            self.file_selected = True

            dpg.set_value(user_data,"Loading...")

            self.update_file(new_file)

            dpg.set_value(user_data,form_string(self.filepath))

            self.update_info_panel(n_hz=self.generated_fourier.binSize,n_milis=self.generated_fourier.TWindow)

    def update_file(self,new_file_path):
        self.filepath = new_file_path
        self.original_file = open(self.filepath,'rb')

        if self.music_init:
            self.stop_music()
            self.load_music()
        else:
            self.init_music()
            self.load_music()        
        
        if self.generated_fourier:
            del self.generated_fourier
            print(f"GC: {gc.collect()}")
            self.generated_fourier = None
        
        self.decoder_ = mp3.Decoder(self.original_file)

        self.generated_fourier = MyFourier(self.decoder_, self.sampleSize)

        self.magnitude = self.generated_fourier.gen(self.hertz_bins) * self.magnitude_scale

        self.maxTicking.change_tick(self.generated_fourier.max)
    
    def init_music(self):
        self.music_lib.init()
        self.music_init = True
        self.load_music()

    def load_music(self):
        if self.file_selected:
            self.music_lib.music.load(self.filepath)
            self.music_lib.music.set_volume(self.volume/100)
    
    def update_volume(self):
        if self.is_playing() and self.volume != self.music_lib.music.get_volume():            
            self.music_lib.music.set_volume(self.volume / 100)

    def set_music_vol(self,sender,value,user_data):
        if value:
            self.volume = value

    def is_playing(self):
        if self.music_init:
            return self.music_lib.music.get_busy()
        return False
        
    def run_music(self):
        if not self.music_init:
            self.select_file(0,0,self.ui_label_widgets.select)

        if self.music_init:
            if not pgm.music.get_busy():
                pgm.music.play()                
                self.music_running = True

    def stop_music(self):
        if self.is_playing():
            self.music_lib.music.stop()
            self.music_running = False
    
    def pause_music(self):
        if self.is_playing():
            self.music_lib.music.pause()
    
    def get_music_pos_ms(self):
        if self.is_playing():
            return self.music_lib.music.get_pos()
        else:
            return 1

    @staticmethod
    def get_screen_dimensions():
        m1 = get_monitors()[0]
        return m1.width,m1.height

    def __init__(self):
        self.running = False
        self.music_init = False
        self.music_running = False
        self.music_lib = pgm
        self.volume = 50

        self.file_selected = False
        self.filepath = "Not Selected"
        self.original_file = None
        self.decoder_ = None

        self.sampleSize = 4096

        self.generated_fourier = None
        
        self.maxTicking = Ticking()

        self.magnitude = 0
        self.magnitude_scale = 0.4
        self.logarithmic_scale = True

        self.scale_to_volume = True
        
        self.hertz_bins = {}
        for member in FINALhzRanges:
            self.hertz_bins[str(member.name)] = member.value

        self.screen_w, self.screen_h = self.get_screen_dimensions()

        self.window_w = int(self.screen_w * 0.5)
        self.window_h = int(self.screen_h * 0.5)

        self.visu_pos = 0.2

        self.main_win_tag = 1
        self.visualizer_win_tag = 2
        self.info_panel_win_tag = 3

        class _ui_label_widgets:
            select = None

        self.ui_label_widgets = _ui_label_widgets()

        self.redraw_thread = None

        self.sync = False

        self.info_panel_tags = {}
    
    def update_info_panel(self,n_hz = None, n_samples = None,n_milis = None):
        if not n_samples:
            n_samples = self.sampleSize
        dpg.configure_item(self.info_panel_tags["samples"],default_value=f"  {n_samples}"[:6])

        if n_hz:
            dpg.configure_item(self.info_panel_tags["hz"],default_value=f"{n_hz}"[:6])

        if n_milis:
            dpg.configure_item(self.info_panel_tags["ms"],default_value=f"  {n_milis*1000}"[0:6])

    def info_panel(self):
        x0 = int(self.window_w/10*6)
        x1 = int(self.window_w/10*8.4)
        y0 = 0
        y1 = int(self.window_h*self.visu_pos)

        size = [x1-x0,y1-y0]

        info_panel = dpg.add_window(label="Info_Panel",tag=self.info_panel_win_tag,pos=[x0,y0],min_size=size,max_size=size,no_move=True,no_resize=True,no_scroll_with_mouse=True,no_scrollbar=True,no_close=True)
       
        self.info_panel_tags["samples"] = dpg.add_text(f"  {self.sampleSize}",label="Samples",show_label=True,parent=info_panel)
        self.info_panel_tags["hz"] = dpg.add_text("00.000",label="Hz/Bin",show_label=True,parent=info_panel)
        self.info_panel_tags["ms"] = dpg.add_text("   0.0",label="ms",show_label=True,parent=info_panel)
    
    def canvas_panel(self):        
        margin = int(self.window_h/35)
        visu_size = [self.window_w,int(self.window_h-(self.window_h*self.visu_pos))]

        visualizer = dpg.add_window(label="Visualizer",tag=self.visualizer_win_tag,pos=[0,int(self.window_h*self.visu_pos)],min_size=visu_size,max_size=visu_size,no_move=True,no_title_bar=True,no_resize=True,no_scroll_with_mouse=True,no_scrollbar=True)
        canvas = dpg.add_drawlist(width=visu_size[0],height=visu_size[1],pos=[0,0],parent=visualizer)
        self.redraw_thread = threading.Thread(target=self.redraw,daemon=True,args=[canvas,visu_size,margin])
        self.redraw_thread.start()
        
    def init_gui(self):
        dpg.create_context()
        
        with dpg.window(label="-",tag=self.main_win_tag) as main_win:
            self.ui_label_widgets.select = dpg.add_text(form_string(self.filepath))
            dpg.add_button(label="Select",
                           user_data=self.ui_label_widgets.select,
                           tag=UiButtonTags.SELECT.value,
                           callback=self.select_file)
            
            dpg.add_button(label="Play", tag=UiButtonTags.RUN.value,
                           callback=self.run_music)

            dpg.add_button(label="Stop", tag=UiButtonTags.STOP.value,
                           callback=self.stop_music)
            
            slider_w = int(self.window_w/8)
            dpg.add_slider_int(min_value=1,max_value=100,pos=(int(self.window_w/10*1),30),label="Volume",width=slider_w,default_value=50,callback=self.set_music_vol,clamped=True,tracked=True)


        self.info_panel()      
        
        self.canvas_panel()

        dpg.create_viewport(title='Audio Visualizer - Frequencies',width=self.window_w,height=self.window_h,resizable=False)
        dpg.set_viewport_pos([self.screen_w/2 - self.window_w/2, self.screen_h/2 - self.window_h/2])
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.main_win_tag, True)

    def start(self):
        self.init_gui()

        self.render_loop()

        self.stop_music()

    def render_loop(self):
        self.running = True
        dpg.start_dearpygui()

    def stop(self):
        dpg.stop_dearpygui()

        if self.original_file:
            self.original_file.close()
        if self.decoder_:
            self.decoder_ = None
            
        self.stop_music()
        
        if self.music_init:
            pgm.quit()
    
    def music_pos_to_tick(self):
        return int(self.get_music_pos_ms()/1000/self.generated_fourier.TWindow)
    
    def redraw(self,canvas,visu_size,margin):
        tick = 0
        delay = 1
        fix = 1      
        col = [87, 96, 150]
        background_col = [0,0,0]
        text_col = (255,255,255)
        text_size = 15
        ratio_spacing = 0.25
        y_margin = 0.05

        txt_values = [v.value for v in FINALhzText]

        bg_size_w = visu_size[0]-margin
        bg_size_h = visu_size[1]-margin

        amount = len(self.hertz_bins.keys())

        o_width = (bg_size_w-margin)/amount
        
        rect_size_w = o_width*ratio_spacing
        spacing = o_width * (1-ratio_spacing)
        
        rect_y0 = bg_size_h*(1-y_margin)
        y_max = rect_y0-(bg_size_h*y_margin)
        
        vol_prct = 1

        while True:
            if dpg.is_dearpygui_running():
                while dpg.is_dearpygui_running():

                    rect_x0 = 0+margin
                    dpg.delete_item(item=canvas,children_only=True)
                    dpg.draw_rectangle((0,0),(bg_size_w,bg_size_h),fill=background_col,color=background_col,parent=canvas)
                    for i in range(0,amount):   
                        if tick >= self.maxTicking.maxTick:
                            tick = 0
                            if self.music_running:
                                self.music_running = False
                        if self.music_running and self.generated_fourier:
                            
                            if not self.sync:
                                tick = 0
                                tick += int(self.get_music_pos_ms()/1000/self.generated_fourier.TWindow) + fix
                                self.sync = True
                            prctn = ((self.generated_fourier.hz_ranges[tick][i]) * vol_prct / self.magnitude) % 1.0
                            if prctn > 0:
                                dpg.draw_rectangle((rect_x0,rect_y0),(rect_x0+rect_size_w,rect_y0-y_max*prctn),fill=col,color=col,parent=canvas)
                        else:
                            tick = 0
                            if self.sync:
                                self.sync = False
                        
                        txt = txt_values[i]
                        tlen = len(txt)

                        dpg.draw_text((rect_x0+(0.5-(0.1*tlen))*rect_size_w,rect_y0+6),text=txt,color=text_col,size=text_size,parent=canvas)
                        rect_x0 += spacing
                        rect_x0 += rect_size_w

                    dpg.draw_line([0,rect_y0+2.5],[bg_size_w,rect_y0+2.5],color=text_col,thickness=1,parent=canvas)
                    dpg.draw_line([0,rect_y0-y_max-2.5],[bg_size_w,rect_y0-y_max-2.5],color=text_col,thickness=1,parent=canvas)
                    dpg.draw_text((bg_size_w-margin*2,rect_y0+6),text="Hz",parent=canvas,color=text_col,size=text_size)
                    
                    if self.generated_fourier:
                        sleep = (self.generated_fourier.TWindow*float(delay))
                    else:
                        sleep = 1
                    time.sleep(sleep)

                    if tick %2 == 0:
                        self.update_volume()
                                        
                        if self.scale_to_volume:
                            vol_prct = ((self.volume*2)/100)
                        else:
                            vol_prct = 1   

                    tick+=delay
            else:
                time.sleep(1)

freq = FrequencyVisualizer()
freq.start()
freq.stop()