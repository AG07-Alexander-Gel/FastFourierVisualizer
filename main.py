import mp3
import pygame.mixer as pgm
import dearpygui.dearpygui as dpg
from tkinter import filedialog
from win32api import GetSystemMetrics
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

class ui_button_tags(Enum):
    RUN : int = 100
    STOP : int = 101
    SELECT : int = 102
    CUSTOM_RANGE : int = 103

class FINAL_hzText(Enum):
    Bass = "150"          #   (0          ,   281.25)
    Low = "450"           #   (328.125    ,   515.625)
    Mid = "1500"          #   (562.5      ,   2015.625)
    Upper = "3500"        #   (2062.5     ,   4031.25)
    Presence = "5000"     #   (4078.125   ,   6000.0)
    Inbet = "9000"        #   (6046.875   ,   13000.0)
    Treble = "15000"      #   (13046.875  ,   20015.625)
    HighP = "20000+"      #   (20062.5    ,   24000.0)     

class FINAL_hzRanges(Enum):
    Bass = 281.25 
    Low = 515.625
    Mid = 2015.625
    Upper = 4031.25
    Presence = 6000.0
    Inbet = 13000.0
    Treble = 20015.625
    HighP = 24000.0
        
class MyFourier:

    def __init__(self,decoder,samplesWindowSize=1024):
        def toMono(buf):
            return ((np.frombuffer(buf, np.int16).reshape(-1,2).sum(axis=1)//2).astype(np.int16))
        
        self.SampleRate = decoder.get_sample_rate()

        self.TWindow = samplesWindowSize/self.SampleRate

        self.binSize = self.SampleRate/samplesWindowSize
        self.binAmount = samplesWindowSize/2
        self.MaxFreq = self.SampleRate/2

        stereo_pcm = decoder.read()
        self.mono_pcm = toMono(stereo_pcm)

        self.samplesSize = samplesWindowSize

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
                
                if(b*self.binSize <= values[kv]):
                    hz += int(spec[b])
                else:
                    hzb[kv] = hz
                    hz = 0
                    kv+=1
            self.hz_ranges[s] = hzb
        
        return np.max(self.hz_ranges)
        

    def gen(self, order : dict,change_ranges : bool = False):
        if not change_ranges:
            while self.current < self.max:
                values = self.mono_pcm[(self.current*self.samplesSize) : ((self.current+1)*self.samplesSize)]
                valuesToWindow = values * np.hamming(self.samplesSize)

                spectral_values = np.fft.fft(valuesToWindow)
            
                self.bin_values[self.current] = abs(spectral_values[:self.neoquist])
                self.current += 1
        
        self.hz_ranges = np.zeros((self.max,len(order.keys())),dtype=np.uint32)       
        return self.gen_hz_ranges(order=order)
            
        
    def printInfo(self):
        print(f"TimeWindow: {str(self.TWindow*1000)[0:5]}ms ; Bin Size: {self.binSize} Hz ; Bin Amount: {self.binAmount} ; MaxFrequencyToCheck: {self.MaxFreq} Hz")

class FrequencyVisualizer:

    def debugging_(self):
        self.is_playing()

    def select_file(self, sender, value, user_data,pre_set_file = None, change_ranges : bool = False):
        if not self.loading_fourier:
            if not pre_set_file:
                new_file = filedialog.askopenfilename(title="Select mp3")
            else:
                new_file = pre_set_file
            if ".mp3" in new_file:        
                self.file_selected = True

                self.update_item_text(self.ui_label_widgets.selected,"Loading...")

                self.loading_fourier = True

                self.update_file(new_file,change_ranges)

                self.update_item_text(self.ui_label_widgets.selected,form_string(new_file))

                self.loading_fourier = False

                self.update_info_panel(n_hz=self.generated_fourier.binSize,n_milis=self.generated_fourier.TWindow)

    def update_file(self,new_file_path, change_ranges : bool = False):
        self.filepath = new_file_path
        self.original_file = open(self.filepath,'rb')

        if self.music_init:
            self.stop_music()
            self.load_music()
        else:
            self.init_music()
            self.load_music()

        if not change_ranges:
            if self.generated_fourier:
                self.generated_fourier = None
                print(f"GC: {gc.collect()}")
                self.generated_fourier = None
            
            self.decoder_ = mp3.Decoder(self.original_file)

        self.generate_from_file(change_ranges=change_ranges)
    
    def generate_from_file(self, change_ranges : bool = False):
        if not self.generated_fourier:
            self.generated_fourier = MyFourier(self.decoder_,self.sampleSize)
        self.magnitude = self.generated_fourier.gen(self.hertz_bins,change_ranges=change_ranges)
        
        self.magnitude * self.magnitude_scale

        self.song_length = self.generated_fourier.max
     
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
            self.music_lib.music.set_volume((self.volume-1)/100)
        if self.scale_to_volume:
            return ((self.volume-1)*1.351)/100
        else:
            return 1.0

    def set_music_vol(self,sender,value,user_data):
        if value:
            self.volume = value

    def is_playing(self):
        if self.music_lib.get_init():
            return self.music_lib.music.get_busy()    
        self.music_init = False
        return False
    
    def update_music_bool(self,nBool):
        self.music_running = nBool
        if nBool:
            self.update_item_text(self.ui_label_widgets.isPlaying,"Playing...")
        else:
            self.update_item_text(self.ui_label_widgets.isPlaying,"Not Playing")
        
    def run_music(self):
        if not self.music_init:
            self.select_file(0,0,None,None)

        if self.music_init:
            if not self.music_lib.music.get_busy():
                self.update_music_bool(True)
                self.music_lib.music.play()           

    def stop_music(self):
        if self.is_playing():
            self.music_lib.music.stop()
            self.update_music_bool(False)
    
    def pause_music(self):
        if self.is_playing():
            self.music_lib.music.pause()
    
    def get_music_pos_ms(self):
        if self.is_playing():
            return self.music_lib.music.get_pos()
        else:
            return self.song_length

    def __init__(self):
        self.music_init = False
        self.music_running = False
        self.music_lib = pgm
        self.volume = 75

        self.file_selected = False
        self.loading_fourier = False
        self.filepath = "Not Selected"
        self.original_file = None
        self.decoder_ = None

        self.running = False

        self.sampleSizeMin = 256
        self.sampleSize = 1024
        self.sampleSizeMax = 8192

        self.generated_fourier = None
        
        self.song_length = 1000000000

        self.abs_minimum = 0.005
        self.magnitude = 0
        self.magnitude_scale = 0.7
        self.bool_alternative_rendering = True
        self.root_scale = 0.65

        self.scale_to_volume = True
        
        self.bool_hertz_bins_custom = False
        self.val_hertz_bins_custom = 100
        self.default_hertz_bins = {}
        self.custom_hertz_bins = {}
        self.hertz_bins = {}

        for member in FINAL_hzRanges:
            self.default_hertz_bins[str(member.name)] = member.value
        
        increment = 24000/self.val_hertz_bins_custom
        t = 24000
        arr = []
        while t >= 0:
            i = int(round(t,0))
            arr.append(i)
            t-=increment
        
        for n in arr[::-1]:
            self.custom_hertz_bins[str(n)] = n


        if self.bool_hertz_bins_custom:
            self.hertz_bins = self.custom_hertz_bins
        else:
            self.hertz_bins = self.default_hertz_bins

        self.screen_w = GetSystemMetrics(0)
        self.screen_h = GetSystemMetrics(1)

        self.reduce_to_screen = 0.6

        self.window_w = int(self.screen_w * self.reduce_to_screen)
        self.window_h = int(self.screen_h * self.reduce_to_screen)

        self.visu_pos = 0.2

        self.main_win_tag = 1
        self.visualizer_win_tag = 2
        self.info_panel_win_tag = 3

        class _ui_label_widgets:
            selected = None
            isPlaying = None
            SampleInput = 201

        self.ui_label_widgets = _ui_label_widgets()

        self.redraw_thread = None

        self.sync = True

        self.info_panel_bool = True
        self.info_panel_tags = {}

        self.dim_amount = 0.9

        self.tick = 0
    
    def update_item_text(self,item_id,text):
        dpg.configure_item(item_id,default_value=text)
    
    def update_item_function(self,item_id,b):
        dpg.configure_item(item_id,enabled=b)
    
    def update_info_panel(self,n_hz = None, n_samples = None,n_milis = None):
        if self.info_panel_bool:
            if not n_samples:
                n_samples = self.sampleSize
            self.update_item_text(self.info_panel_tags["samples"],f"  {n_samples}"[:6])

            if n_hz:
                self.update_item_text(self.info_panel_tags["hz"],f"{n_hz}"[:6])

            if n_milis:
                self.update_item_text(self.info_panel_tags["ms"],f"  {n_milis*1000}"[0:6])
    
    def sampleInput(self,sender, value, user_data):
        if dpg.is_dearpygui_running():
            newVal = 0
            if self.sampleSize > value:
                newVal = self.sampleSize/2
            else:
                newVal = self.sampleSize*2
            newVal = max(min(int(newVal),self.sampleSizeMax),self.sampleSizeMin)
            dpg.set_value(self.ui_label_widgets.SampleInput,newVal)
            self.sampleSize = newVal
    
    @staticmethod
    def cstmRangeString(val : bool) -> str:
        return "Custom Ranges: " + ("On" if val else "Off")

    def changeCustomRangeInput(self, sender, change = None):
        if not self.music_running:
            if not change:
                self.bool_hertz_bins_custom = not self.bool_hertz_bins_custom
            else:
                self.bool_hertz_bins_custom = change

            self.hertz_bins = self.custom_hertz_bins if self.bool_hertz_bins_custom else self.default_hertz_bins
            
            self.select_file(0,0,None,self.filepath,change_ranges=True)
                
            if dpg.is_dearpygui_running():
                dpg.set_item_label(ui_button_tags.CUSTOM_RANGE.value,self.cstmRangeString(self.bool_hertz_bins_custom))            

    def info_panel(self):
        self.info_panel_bool = True
        x0 = int(self.window_w/10*6)
        x1 = int(self.window_w/10*7.4)
        y0 = 0
        y1 = int(self.window_h*self.visu_pos)

        size = [x1-x0,y1-y0]

        info_panel = dpg.add_window(label="Current Song Info",tag=self.info_panel_win_tag,pos=[x0,y0],min_size=size,max_size=size,no_move=True,no_resize=True,no_close=True,collapsed=True)
       
        self.info_panel_tags["samples"] = dpg.add_text(f"  {self.sampleSize}",label="Samples",show_label=True,parent=info_panel)
        self.info_panel_tags["hz"] = dpg.add_text("00.000",label="Hz/Bin",show_label=True,parent=info_panel)
        self.info_panel_tags["ms"] = dpg.add_text("   0.0",label="ms",show_label=True,parent=info_panel)
        
    def init_gui(self):
        dpg.create_context()
        
        with dpg.window(label="-",tag=self.main_win_tag,no_background=True) as main_win:
            self.ui_label_widgets.selected = dpg.add_text(form_string(self.filepath))

            dpg.add_button(label="Select",
                           tag=ui_button_tags.SELECT.value,
                        callback=self.select_file)
            
            dpg.add_button(label="Play",tag=ui_button_tags.RUN.value,
                        callback=self.run_music)

            dpg.add_button(label="Stop",tag=ui_button_tags.STOP.value,
                        callback=self.stop_music)
            
            dpg.add_input_int(label="Size",tag=self.ui_label_widgets.SampleInput,default_value=self.sampleSize,width=self.window_h/9,min_value=self.sampleSizeMin,max_value=self.sampleSizeMax,callback=self.sampleInput)

            
            dpg.add_button(label=self.cstmRangeString(self.bool_hertz_bins_custom),tag=ui_button_tags.CUSTOM_RANGE.value,callback=self.changeCustomRangeInput)
            
            slider_w = self.window_w/8
            dpg.add_slider_int(min_value=1,max_value=100,pos=(self.window_w/10*1,30),label="Volume",width=slider_w,default_value=self.volume,callback=self.set_music_vol,clamped=True,tracked=True,user_data=self.sampleSize)

            leftmost = self.window_w/10*0.04
            upmost = self.window_h/16*2.76
            
            dpg.draw_line(p1=(-leftmost,self.window_h/16*5),p2=(-leftmost,-40),color=[150,150,150],thickness=4)            
            self.ui_label_widgets.isPlaying = dpg.add_text("Not Playing",pos=[leftmost+2,upmost],color=[255,255,255])
            dpg.draw_rectangle((-leftmost*0.5,upmost*0.9),pmax=((leftmost*15,upmost*1.1)),color=[75,75,75])

        if self.info_panel_bool:
            self.info_panel()      
        
        self.canvas_panel()

        dpg.create_viewport(title='Audio Visualizer - Frequencies',width=self.window_w,height=self.window_h,resizable=False)
        dpg.set_viewport_pos([self.screen_w/2 - self.window_w/2, self.screen_h/2 - self.window_h/2])
        dpg.set_viewport_small_icon("small_icon.ico")
        dpg.set_viewport_large_icon("large_icon.ico")
        dpg.set_viewport_clear_color([0,0,0])
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.main_win_tag, True)
    
    def canvas_panel(self):        
        margin = 30
        visu_size = [self.window_w,int(self.window_h-(self.window_h*self.visu_pos))]

        visualizer = dpg.add_window(label="Visualizer",tag=self.visualizer_win_tag,pos=[0,self.window_h*self.visu_pos],min_size=visu_size,max_size=visu_size,no_move=True,no_title_bar=True,no_resize=True,no_scroll_with_mouse=True,no_scrollbar=True)
        canvas = dpg.add_drawlist(width=visu_size[0],height=visu_size[1],pos=[0,0],parent=visualizer)
        self.redraw_thread = threading.Thread(target=self.redraw,daemon=True,args=[canvas,visu_size,margin])
    
    def start_redraw_thread(self):
        self.redraw_thread.start()

    def render_loop(self):
        dpg.start_dearpygui()
    
    def start(self):
        self.init_gui()

        self.running = True

        self.start_redraw_thread()

        self.render_loop()

        self.running = False

        self.stop_music()

    def stop(self):
        dpg.stop_dearpygui()

        if self.original_file:
            self.original_file.close()
        if self.decoder_:
            self.decoder_ = None
            
        self.stop_music()
        
        if self.music_init:
            self.music_lib.quit()
    
    def music_pos_to_tick(self):
        return int(self.get_music_pos_ms()/1000/self.generated_fourier.TWindow)

    @staticmethod
    def alt_rendering(val,max_val,root_sc, bl : bool = False):
        correction = 0.00000001
        idk = True

        mult = 1.0
        if bl:
            even = 0.2     
        else:
            even = 0.0
            root_sc *= 1.2                   
            
            if val <= max_val*0.3:
                mult = 1.2
            elif val > max_val*0.85:
                mult = 0.8

        
        if idk:
            return (val**root_sc)*mult/(max_val**root_sc)-even
        return math.log(val+correction)/math.log(max_val+correction)

    @staticmethod
    def negative_color(color):
        return [255-color[0],255-color[1],255-color[2]]
    
    @staticmethod
    def dim_color(color,dim):
        return [int(c*dim) for c in color]
    
    def redraw(self,canvas,visu_size,margin):
        step = 1
        fix = 0      
        col_n = [87, 96, 150]
        col_n_dim = self.dim_color(col_n,self.dim_amount)
        col_over = [150,50,30]
        background_col = [0,0,0]
        text_col = (255,255,255)
        text_size = 15
        ratio_spacing = 0.25
        y_margin = 0.09
        dist_to_line = 0.5
        
        bg_size_w = visu_size[0]-margin
        bg_size_h = visu_size[1]-margin*1.75

        rect_y0 = bg_size_h*(1-y_margin)
        y_max = rect_y0-(bg_size_h*y_margin)
        
        vol_prct = 1.0

        #update when bool changes for custom range
        loop_custom_ranges = not self.bool_hertz_bins_custom
        amount = 0
        txt_values = []
        o_width = 0
        rect_size_w = 0
        spacing = 0
        
        reduce_amount = 0.65

        self.draw_background(canvas=canvas,bg_w=bg_size_w,bg_h=bg_size_h,bg_col=background_col,margin=margin,text_col=text_col,text_size=text_size,yFix=y_margin,rectMax=rect_y0,yMax=y_max)

        while self.running:
        
            #poll custom range
            if loop_custom_ranges != self.bool_hertz_bins_custom:
                loop_custom_ranges = self.bool_hertz_bins_custom

                
                if not loop_custom_ranges:
                    txt_values = [v.value for v in FINAL_hzText]
                else:
                    txt_values = ["" for h in self.custom_hertz_bins]

                amount = len(self.hertz_bins.keys())

                if self.bool_hertz_bins_custom:
                    amount = int(amount*reduce_amount)

                o_width = (bg_size_w-margin*4.5)/amount        
                rect_size_w = o_width*ratio_spacing
                spacing = o_width * (1-ratio_spacing)

            if dpg.is_dearpygui_running():


                rect_x0 = 0+margin*3

                #redraw-step : Clear
                self.clear_screen(screen=canvas)
                
                self.draw_background(canvas=canvas,bg_w=bg_size_w,bg_h=bg_size_h,bg_col=background_col,margin=margin,text_col=text_col,text_size=text_size,yFix=y_margin,rectMax=rect_y0,yMax=y_max)


                #Change and update behaviour when self.tick reaches end

                if self.tick >= self.song_length:
                    self.tick = 0
                    print("done")
                    if self.music_running:
                        self.update_music_bool(False)              
                
                self.sync_tick_to_music(fix)                

                for i in range(0,amount):

                    if self.music_running and self.generated_fourier:
                        
                        self.draw_bars_rect(canvas,i,vol_prct,rect_x0,rect_y0,rect_size_w,y_max,dist_to_line,col_n,col_over,col_n_dim,margin,bg_size_w)  

                    else:
                        self.tick = 0
                    
                    txt = txt_values[i]
                    tlen = len(txt)

                    dpg.draw_text((rect_x0+(0.5-(0.09*tlen))*rect_size_w,rect_y0+6),text=txt,color=text_col,size=text_size,parent=canvas)
                    rect_x0 += spacing
                    rect_x0 += rect_size_w

                
                
                if(self.generated_fourier):
                    sleep = (self.generated_fourier.TWindow*float(step))                    
                else:
                    sleep = 1
                time.sleep(sleep)

                if(self.tick %2 == 0):
                    vol_prct = self.update_volume()
                    
                self.tick+=step
            else:
                time.sleep(0.5)
    
    def draw_bars_rect(self,canvas,i,vol_prct,rect_x0,rect_y0,rect_size_w,y_max,dist_to_line,col_n,col_over,col_n_dim,margin,bg_size_w):

        val = self.generated_fourier.hz_ranges[self.tick][i]* vol_prct
        maximum = self.magnitude

        if not self.bool_alternative_rendering:
            percentage = val/maximum
        else:
            percentage = self.alt_rendering(val,maximum,self.root_scale,self.bool_hertz_bins_custom)

        overFlow = 0
        if percentage > 1.0:
            overFlow = percentage-1.0
            percentage = 1.0
        elif percentage < self.abs_minimum:
            percentage = self.abs_minimum
        
        if overFlow > 0:
            c = col_n_dim
        else:
            c = col_n

        dpg.draw_rectangle((rect_x0,rect_y0),(rect_x0+rect_size_w,rect_y0-(y_max-dist_to_line)*percentage),fill=c,color=c,parent=canvas)
        if overFlow > 0:
            dpg.draw_rectangle((rect_x0,rect_y0),(rect_x0+rect_size_w,rect_y0-(y_max-dist_to_line)*overFlow),fill=col_over,color=col_over,parent=canvas)
    
    def clear_screen(self,screen):
        dpg.delete_item(item=screen,children_only=True)
    
    def draw_background(self,canvas,bg_col,bg_w,bg_h,margin,text_col,text_size,yMax,yFix,rectMax):
        dpg.draw_rectangle((0,0),(bg_w,bg_h),fill=bg_col,color=bg_col,parent=canvas)

        dpg.draw_line([0,rectMax+2.5],[bg_w,rectMax+2.5+yFix],color=text_col,thickness=1,parent=canvas)
        dpg.draw_line([0,rectMax-yMax-2.5],[bg_w,rectMax-yMax-2.5-yFix],color=text_col,thickness=1,parent=canvas)
        dpg.draw_text((bg_w-margin,rectMax+6),text="Hz",parent=canvas,color=text_col,size=text_size)
    
    def sync_tick_to_music(self,fix):
        if(self.tick %6 == 0 and self.sync and self.music_running and self.tick < self.song_length):
            self.tick = int(round(self.get_music_pos_ms()/1000/self.generated_fourier.TWindow,0)) + fix

freq = FrequencyVisualizer()
freq.start()
freq.stop()