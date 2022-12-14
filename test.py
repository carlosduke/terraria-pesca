import tkinter
from tkinter import filedialog
import screeninfo
import cv2
import numpy as np
import json

from PIL import Image
from PIL import ImageTk
from PIL import Image, ImageGrab

import pyautogui
import threading
import time
from datetime import datetime

import configparser

running = True

def monitor_loop(app):
    while app.running:
        pos = pyautogui.position()
        app.update(pos.x, pos.y)
        app.process_image(app.image)

        time.sleep(1/app.frames)
    print('stop loop')



def start_monitor(app):
    app.image_path = None
    app.running = True
    t = threading.Thread(target=monitor_loop, args=(app,)).start()
    #app.set_thread(t)

def stop_monitor(app):
    app.stop()

def record(app):
    app.recording = True
    x,y = app.pos
    app.start_record()
    app.update(x,y)


class Application:
    def __init__(self, master=None):
        self.buffer = []
        self.buffer_idx = 0

        self.count = -1
        self.last_sent = time.time()

        self.running = False
        self.recording = False
        self.fishing = False
        self.frames = 30
        self.cap = None

        self.env_name = tkinter.StringVar()
        self.env_name.set('--select--')
        self.envs = ['DEFAULT']
        self.load_config()
        self.mount_gui(master)

        #self.image_path = 'C:/Users/carlo/Documents/desenv/projs/terraria-pesca/20221103T213720.mp4'
        self.load_image()

    def mount_gui(self, master=None):
        self.mount_config(master)
        self.mount_preview(master)

        self.update()
    
    def mount_config(self, master=None):
        self.fconfig = tkinter.Frame(master)
        self.fconfig.pack(side='left')

        #label status
        self.lstatus = tkinter.Label(self.fconfig)
        self.lstatus['text'] = 'waiting...'
        self.lstatus.pack()

        #Control
        self.fcontrol = tkinter.Frame(self.fconfig)
        self.fcontrol.pack()

        #Btn start monitor
        self.bstart_monitor = tkinter.Button(self.fcontrol)
        self.bstart_monitor['text'] = 'Start'
        self.bstart_monitor['command'] = lambda: start_monitor(self)
        self.bstart_monitor['state'] = 'enable' if self.running else 'disabled'
        self.bstart_monitor.pack(side='left')

        #Btn Recorder start
        self.brecorder = tkinter.Button(self.fcontrol)
        self.brecorder['text'] = 'Record'
        self.brecorder['command'] = lambda: record(self)
        self.brecorder['state'] = 'active' if self.recording else 'disabled'
        self.brecorder.pack(side='left')

        #Btn Recorder stop
        self.bstop_monitor = tkinter.Button(self.fcontrol)
        self.bstop_monitor['text'] = 'Stop'
        self.bstop_monitor['command'] = lambda: stop_monitor(self)
        self.bstop_monitor["state"] = 'enable' if self.running else 'disabled'
        self.bstop_monitor.pack(side='left')

        #Btn Recorder stop
        self.bfishing = tkinter.Button(self.fcontrol)
        self.bfishing["text"] = 'Fishing *' if self.fishing else 'Fishing'
        self.bfishing['command'] = lambda: self.handle_fishing_btn()
        self.bfishing.pack(side='left')

        #Configs
        self.fconfigenv = tkinter.Frame(self.fconfig)
        self.fconfigenv.pack()

        self.cenv = tkinter.ttk.Combobox(self.fconfigenv)
        self.cenv['values'] = self.envs
        self.cenv['textvariable'] = self.env_name
        self.cenv.bind('<<ComboboxSelected>>', lambda e: self.change_env(e))
        self.cenv.pack(side = 'left')

        self.baddenv = tkinter.Button(self.fconfigenv)
        self.baddenv['text'] = 'Add'
        self.baddenv['command'] = lambda: self.add_env(
            tkinter.simpledialog.askstring(title="Environment", prompt="Env name:")
        )
        self.baddenv.pack(side = 'left')

        #Widget itens
        self.fcomponents = tkinter.Frame(self.fconfig)
        self.fcomponents.pack()
        
        #Sense
        self.fsense = tkinter.Frame(self.fcomponents)
        self.fsense.pack()
        self.lsense = tkinter.Label(self.fsense)
        self.lsense['text'] = 'Sense: '
        self.lsense.pack(side = 'left')

        self.esense = tkinter.Entry(self.fsense)
        self.esense.insert(0, self.sense)
        self.esense.pack()

        #Width images
        self.fwidth = tkinter.Frame(self.fcomponents)
        self.fwidth.pack()
        self.lsize_width = tkinter.Label(self.fwidth)
        self.lsize_width['text'] = 'Width: '
        self.lsize_width.pack(side = 'left')

        width,height = self.size
        self.esize_width = tkinter.Entry(self.fwidth)
        self.esize_width.insert(0, width)
        self.esize_width.pack()

        #Height images
        self.fheight = tkinter.Frame(self.fcomponents)
        self.fheight.pack()
        self.lsize_height = tkinter.Label(self.fheight)
        self.lsize_height['text'] = 'Height: '
        self.lsize_height.pack(side = 'left')

        self.esize_height = tkinter.Entry(self.fheight)
        self.esize_height.insert(0, height)
        self.esize_height.pack(side = 'left')

        #Scale threshold
        self.fthreshold = tkinter.Frame(self.fcomponents)
        self.fthreshold.pack()
        self.lsize_threshold = tkinter.Label(self.fthreshold)
        self.lsize_threshold['text'] = 'Threshold: '
        self.lsize_threshold.pack(side = 'left')

        self.sthreshold = tkinter.Scale(self.fthreshold, from_=1, to=255, orient=tkinter.HORIZONTAL)
        self.sthreshold.set(self.threshold)
        self.sthreshold['command'] = lambda e: self.configure()
        self.sthreshold.pack(side = 'left')

        #GaussianBlur
        self.fgaussianblur = tkinter.Frame(self.fcomponents)
        self.fgaussianblur.pack()

        self.gaussianblur_label = tkinter.Label(self.fgaussianblur)
        self.gaussianblur_label['text'] = 'GaussianBlur'
        self.gaussianblur_label.pack(side='left')

        self.fgaussianblur_v = tkinter.Frame(self.fgaussianblur)
        self.fgaussianblur_v.pack(side='left')
        
        gv1,gv2 = self.gaussianblur
        self.fgaussianblur_v1 = tkinter.Scale(self.fgaussianblur_v, from_=1, to=29, orient=tkinter.HORIZONTAL)
        self.fgaussianblur_v1.set(gv1)
        self.fgaussianblur_v1['command'] = lambda e: self.configure()
        self.fgaussianblur_v1.pack()

        self.fgaussianblur_v2 = tkinter.Scale(self.fgaussianblur_v, from_=1, to=29, orient=tkinter.HORIZONTAL)
        self.fgaussianblur_v2.set(gv2)
        self.fgaussianblur_v2['command'] = lambda e: self.configure()
        self.fgaussianblur_v2.pack()

        #position
        #GaussianBlur
        self.fposition = tkinter.Frame(self.fcomponents)
        self.fposition.pack()

        self.lposition = tkinter.Label(self.fposition)
        self.lposition['text'] = 'Position'
        self.lposition.pack(side='left')

        self.fposition_v = tkinter.Frame(self.fposition)
        self.fposition_v.pack(side='left')
        
        posx,posy = self.pos
        screen = self.screens[self.screen_idx]
        wscreen = screen.width
        hscreen = screen.height
        self.sposx = tkinter.Scale(self.fposition_v, from_=0, to=wscreen, orient=tkinter.HORIZONTAL)
        self.sposx.set(posx)
        self.sposx['command'] = lambda e: self.configure()
        self.sposx.pack()

        self.sposy = tkinter.Scale(self.fposition_v, from_=0, to=hscreen, orient=tkinter.HORIZONTAL)
        self.sposy.set(posy)
        self.sposy['command'] = lambda e: self.configure()
        self.sposy.pack()

        #Monitors
        self.fmonitors = tkinter.Frame(self.fcomponents)
        self.fmonitors.pack()
        self.lmonitors = tkinter.Label(self.fmonitors)
        self.lmonitors['text'] = 'Monitors'
        self.lmonitors.pack()

        self.lsmonitors = tkinter.Listbox(self.fmonitors)
        self.lsmonitors['height'] = len(self.screens)
        for monitor in self.screens:
            if monitor.is_primary:
               self.lsmonitors.insert(tkinter.END, f'* {monitor.width}x{monitor.height}')
        self.lsmonitors.bind('<<ListboxSelect>>', lambda e: self.select_screen(self.lsmonitors.curselection()))
        self.lsmonitors.pack()

        self.bfile = tkinter.Button(self.fconfig)
        self.bfile['text'] = 'Open...'
        self.bfile['command'] = lambda: self.open_file()
        self.bfile.pack()

        self.bconfig = tkinter.Button(self.fconfig)
        self.bconfig['text'] = 'Configure'
        self.bconfig['command'] = lambda: self.configure()
        self.bconfig.pack()
    
    def add_env(self, env_name):
        if env_name not in self.envs:
            self.envs.append(env_name)
        
        self.cenv['values'] = self.envs
        #self.cenv.insert(tkinter.END, env_name)

    def mount_preview(self, master=None):
        self.fpreview = tkinter.Frame(master)
        self.fpreview.pack(side='left')

        self.fpreview_imgs = tkinter.Frame(self.fpreview)
        self.fpreview_imgs.pack()

        self.sframes = tkinter.Scale(self.fpreview_imgs, from_=0, to=0, orient=tkinter.VERTICAL)
        self.sframes['command'] = lambda e: self.handle_configure()
        self.sframes['tickinterval']=1
        self.sframes.pack(side = 'left')

        self.limage_orig = tkinter.Label(self.fpreview_imgs)
        self.limage_orig.pack(side = 'left')

        self.limage_gray = tkinter.Label(self.fpreview_imgs)
        self.limage_gray.pack(side = 'left')

        self.limage_process = tkinter.Label(self.fpreview_imgs)
        self.limage_process.pack(side = 'left')

        #ranges
        #Lower
        self.frange_lower = tkinter.Frame(self.fpreview)
        self.frange_lower.pack(side='left')

        #Red
        self.frange_lower_r = tkinter.Frame(self.frange_lower)
        self.frange_lower_r.pack()

        self.srange_lower_r = tkinter.Scale(self.frange_lower_r, from_=0, to=255, orient=tkinter.HORIZONTAL)
        self.srange_lower_r['command'] = lambda e: self.handle_configure()
        self.srange_lower_r.set(self.boundary_lower[0])
        self.srange_lower_r.pack()

        #Green
        self.frange_lower_g = tkinter.Frame(self.frange_lower)
        self.frange_lower_g.pack()

        self.srange_lower_g = tkinter.Scale(self.frange_lower_g, from_=0, to=255, orient=tkinter.HORIZONTAL)
        self.srange_lower_g['command'] = lambda e: self.handle_configure()
        self.srange_lower_g.set(self.boundary_lower[1])
        self.srange_lower_g.pack()

        #Blue
        self.frange_lower_b = tkinter.Frame(self.frange_lower)
        self.frange_lower_b.pack()

        self.srange_lower_b = tkinter.Scale(self.frange_lower_b, from_=0, to=255, orient=tkinter.HORIZONTAL)
        self.srange_lower_b['command'] = lambda e: self.handle_configure()
        self.srange_lower_b.set(self.boundary_lower[2])
        self.srange_lower_b.pack()


        #Upper
        self.frange_upper = tkinter.Frame(self.fpreview)
        self.frange_upper.pack(side='left')

        #Red
        self.frange_upper_r = tkinter.Frame(self.frange_upper)
        self.frange_upper_r.pack()

        self.srange_upper_r = tkinter.Scale(self.frange_upper_r, from_=0, to=255, orient=tkinter.HORIZONTAL)
        self.srange_upper_r['command'] = lambda e: self.handle_configure()
        self.srange_upper_r.set(self.boundary_upper[0])
        self.srange_upper_r.pack()

        #Green
        self.frange_upper_g = tkinter.Frame(self.frange_upper)
        self.frange_upper_g.pack()

        self.srange_upper_g = tkinter.Scale(self.frange_upper_g, from_=0, to=255, orient=tkinter.HORIZONTAL)
        self.srange_upper_g['command'] = lambda e: self.handle_configure()
        self.srange_upper_g.set(self.boundary_upper[1])
        self.srange_upper_g.pack()

        #Blue
        self.frange_upper_b = tkinter.Frame(self.frange_upper)
        self.frange_upper_b.pack()

        self.srange_upper_b = tkinter.Scale(self.frange_upper_b, from_=0, to=255, orient=tkinter.HORIZONTAL)
        self.srange_upper_b['command'] = lambda e: self.handle_configure()
        self.srange_upper_b.set(self.boundary_upper[2])
        self.srange_upper_b.pack()

        self.load_image()
        self.process_image(self.image)

    def handle_configure(self):
        self.configure()
        self.load_image()
        self.process_image(self.image)

    def load_image(self):
        width, height = self.size
        if self.image_path == None:
            img = np.ones((width,height,3), np.uint8)*255
            #print(self.pos)

            x,y = self.pos
            screen = self.screens[self.screen_idx]
            wscreen = screen.width
            hscreen = screen.height


            if x - self.view_size < 0: x = self.view_size
            if y - self.view_size < 0: y = self.view_size

            if x + self.view_size > wscreen: x = wscreen-self.view_size*2
            if y + self.view_size > hscreen: y = hscreen-self.view_size*2

            img = ImageGrab.grab((
                x-int(self.view_size),
                y-int(self.view_size),
                x+int(self.view_size),
                y+int(self.view_size)
            ))
            img = np.array(img)
        elif self.image_path.lower().endswith('.png'):
            img = cv2.imread(self.image_path)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif self.image_path.lower().endswith('.mp4'):
            start = 3980
            if not self.cap:
                self.cap = cv2.VideoCapture(self.image_path)

                #print((self.cap.get(cv2.CAP_PROP_FRAME_COUNT)))
                self.sframes['to'] = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) -1 - start

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, start + self.sframes.get())
            ok, img = self.cap.read()
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        w,h,l = img.shape
        prop_w = width/w
        prop_h = height/h

        #print(img.shape, prop_w, prop_h)
        #print(int(w*prop_w), int(h*prop_h))
        img = cv2.resize(img, (int(w*prop_w), int(h*prop_h)), cv2.INTER_AREA)
        
        
        #print(img[125, 240].shape, )

        self.image = img

        image = Image.fromarray(self.image)
        image = ImageTk.PhotoImage(image)
        self.limage_orig.configure(image=image)
        self.limage_orig.image = image
        #print(img.shape)
    
    def open_file(self):
        filename = tkinter.filedialog.askopenfilename(
            initialdir = ".",
            title = "Select a File",
            filetypes = (
                ("Png Images", "*.png"),
                ("MP4 Files", "*.mp4"),
                ("all files", "*.*")

            )
        )
        if not filename:
            return
        
        print(f'Opened: {filename}')
        self.image_path = filename
        
        self.load_image()
        self.process_image(self.image)

    def process_image(self, image):
        g1,g2 = self.gaussianblur
        lower = np.array(self.boundary_lower, dtype='uint8')
        upper = np.array(self.boundary_upper, dtype='uint8')

        #proc = cv2.GaussianBlur(image, (g1,g2), 0)
        proc = cv2.inRange(image, lower, upper)
        proc = cv2.bitwise_and(image, image, mask= proc)

        image_proc = proc
        img_proc = Image.fromarray(image_proc)
        img_proc = ImageTk.PhotoImage(img_proc)
        self.limage_gray.configure(image=img_proc)
        self.limage_gray.image = img_proc

        proc = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
        th = self.threshold
        th, proc = cv2.threshold(proc, th, 255, cv2.THRESH_BINARY)

        #image_proc = np.hstack((image_proc, proc))
        #proc = image
        #cv2.circle(proc, (125,50), 30, (191,24,3), -1)
        #cv2.circle(proc, (125,150), 30, (228,29,3), -1)
        # th = self.threshold
        # th, proc = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
        
        # gray = Image.fromarray(gray)
        # gray = ImageTk.PhotoImage(gray)
        # self.limage_gray.configure(image=gray)
        # self.limage_gray.image = gray

        p = Image.fromarray(proc)
        p = ImageTk.PhotoImage(p)
        self.limage_process.configure(image=p)
        self.limage_process.image = p

        if len(self.buffer) == 0:
            for i in range(0, 3):
                self.buffer.append(proc)
        
        self.buffer_idx = (self.buffer_idx + 1)%len(self.buffer)
        self.buffer[self.buffer_idx] = proc
        t0, t1, t2 = self.buffer
        d1 = cv2.absdiff(t0, t1)
        d2 = cv2.absdiff(t1,t2)
        res = cv2.bitwise_or(d1,d2)
        #print(res.shape)
        try:
            count = cv2.countNonZero(res)
        except:
            count = 1
        if count == 0: count = 1
        
        if self.count == -1:
            self.count = count
        
        if not self.running or not self.fishing:
            return
        diff = abs(self.count - count)
        self.lstatus['text'] = f'{self.sense} - {diff}, {(time.time() - self.last_sent)}'

        if diff > self.sense and (time.time() - self.last_sent) > 3:
            self.last_sent = time.time()
            pyautogui.mouseDown()
            time.sleep(0.02)
            pyautogui.mouseUp()

            time.sleep(0.5)
            pyautogui.mouseDown()
            time.sleep(0.02)
            pyautogui.mouseUp()

        # res = Image.fromarray(res)
        # res = ImageTk.PhotoImage(res)
        # self.limage_process.configure(image=res)
        # self.limage_process.image = res

    def select_screen(self, selected):
        self.screen_idx = selected[0]

        screen = self.screens[self.screen_idx]
        wscreen = screen.width
        hscreen = screen.height
        self.sposx['to'] = wscreen
        self.fposy['to'] = hscreen

    def change_env(self, e):
        print(self.env_name.get(), self.envs)

        self.load_config()

        self.sthreshold.set(self.threshold)

        gv1,gv2 = self.gaussianblur
        self.fgaussianblur_v1.set(gv1)
        self.fgaussianblur_v2.set(gv2)

        posx,posy = self.pos
        self.sposx.set(posx)
        self.sposy.set(posy)

        self.srange_lower_r.set(self.boundary_lower[0])
        self.srange_lower_g.set(self.boundary_lower[1])
        self.srange_lower_b.set(self.boundary_lower[2])

        self.srange_upper_r.set(self.boundary_upper[0])
        self.srange_upper_g.set(self.boundary_upper[1])
        self.srange_upper_b.set(self.boundary_upper[2])

        self.esense.delete(0, 'end')
        self.esense.insert(0, self.sense)

        self.configure()

    def load_config(self):
        self.config = configparser.ConfigParser()
        self.config.read('./config.ini')

        self.envs = self.config.sections()
        #TODO: Verificar
        if 'DEFAULT' not in self.envs:
            self.envs.append('DEFAULT')

        cur_env = self.env_name.get()
        if cur_env not in self.envs:
            cur_env = 'DEFAULT'

        self.size = (
            int(self.config[cur_env].get('size_with', 350)),
            int(self.config[cur_env].get('size_height', 350)),
        )

        self.threshold = int(self.config[cur_env].get('threshold', 350))
        self.gaussianblur = (
            int(self.config[cur_env].get('gaussianblur_v1', 350)),
            int(self.config[cur_env].get('gaussianblur_v2', 350))
        )
        self.pos = (
            int(self.config[cur_env].get('screen_x', 0)),
            int(self.config[cur_env].get('screen_y', 0))
        )
        self.image_path = None
        self.view_size = int(self.config[cur_env].get('view_size', 50))

        self.screens = screeninfo.get_monitors()
        self.screen_idx = int(self.config[cur_env].get('screen_idx', 0))

        self.sense = int(self.config[cur_env].get('sense', 0))
        self.boundary_lower = json.loads(self.config[cur_env].get('boundary_lower', '[0,0,0]'))
        self.boundary_upper = json.loads(self.config[cur_env].get('boundary_upper', '[255,255,255]'))

        #print(cur_env, self.boundary_lower, self.boundary_upper)

    def save_config(self):
        cur_env = self.env_name.get()
        #print('Start save', cur_env, self.envs)
        if cur_env == '--select--': return
        if cur_env not in self.envs:
            self.config.add_section(cur_env)
        
        w,h = self.size
        self.config[cur_env]['size_with'] = str(w)
        self.config[cur_env]['size_height'] = str(h)

        self.config[cur_env]['threshold'] = str(self.threshold)

        g1,g2 = self.gaussianblur
        self.config[cur_env]['gaussianblur_v1'] = str(g1)
        self.config[cur_env]['gaussianblur_v2'] = str(g2)

        x,y = self.pos
        self.config[cur_env]['screen_x'] = str(x)
        self.config[cur_env]['screen_y'] = str(y)
        self.config[cur_env]['view_size'] = str(self.view_size)

        self.config[cur_env]['screen_idx'] = str(self.screen_idx)
        self.config[cur_env]['sense'] = str(self.sense)

        self.config[cur_env]['boundary_lower'] = str(self.boundary_lower)
        self.config[cur_env]['boundary_upper'] = str(self.boundary_upper)

        with open('./config.ini', 'w') as f:
            self.config.write(f)

    def configure(self):
        # self.gaussianblur = (21,21)
        # self.image_path = './sample4.png'

        self.size = (
            int(self.esize_width.get()),
            int(self.esize_height.get()) 
        )
        
        self.threshold = self.sthreshold.get()

        self.gaussianblur = (
            self.fgaussianblur_v1.get(),
            self.fgaussianblur_v2.get()
        )

        # self.load_image()
        # self.process_image(self.image)


        self.pos = (
            self.sposx.get(),
            self.sposy.get()
        )

        self.sense = int(self.esense.get())

        #print(self.size, self.threshold, self.gaussianblur, self.pos)
        self.boundary_lower = [
            self.srange_lower_r.get(),
            self.srange_lower_g.get(),
            self.srange_lower_b.get()
        ]

        self.boundary_upper = [
            self.srange_upper_r.get(),
            self.srange_upper_g.get(),
            self.srange_upper_b.get()
        ]
        
    def start_record(self):
        self.video_writer = cv2.VideoWriter(
            './' + datetime.now().strftime('%Y%m%dT%H%M%S') + '.mp4',
            cv2.VideoWriter_fourcc(*'MP4V'),
            self.frames,
            self.size
        )
    
    def stop(self):
        self.running = False
        
        if self.recording:
            self.video_writer.release()
        
        self.recording = False

        x,y = self.pos
        self.update(x,y)

    def update(self, x = 0,y = 0):
        self.lstatus['text'] = f'X: {x}, Y: {y}'

        self.bstart_monitor['state'] = 'disabled' if self.running else 'active'
        self.brecorder['state'] = 'disabled' if self.recording else 'active'
        self.bstop_monitor['state'] = 'active' if self.running else 'disabled'

        self.load_image()
        if self.recording:
            self.video_writer.write(cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR))

        #self.process_image(self.image)

    def handle_fishing_btn(self):
        self.fishing = not self.fishing
        self.bfishing["text"] = 'Fishing *' if self.fishing else 'Fishing'


def verify_image(img):
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img_gray

def main():
    root = tkinter.Tk()
    root.wm_attributes("-topmost", 1)
    app = Application(root)
    root.mainloop()
    app.save_config()
    app.runnig = False
    

if __name__ == '__main__':
    main()