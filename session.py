import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import numpy as np
import time
from PIL import Image, ImageTk, ImageDraw
from PIL.ExifTags import TAGS
from collections import OrderedDict
import json
import exifread
from utils import *
from collections import OrderedDict
import csv
import ast

debug = False

class PhenoSession(tk.Tk):
    """
    Class for managing a GUI session
    """
    def __init__(self, parent, load):

        # member variables
        self.images = OrderedDict()
        self.roi = tk.StringVar() # current roi selection
        self.curframe = None
        self.curcoords = None
        self.done = {}
        self.curdir = None

        # get files and curdir
        if load:
            self.load_session()

        else:
            imfiles = list(filedialog.askopenfilenames(initialdir=self.curdir))

            self.curdir = os.path.dirname(imfiles[0])
            for imfile in imfiles:
                # populate dictionary with images
                img = myImage(imfile)
                self.images[img.name] = img

        # create gui
        self.create_gui(parent)

    def save(self):
        """ 
        Save the output
        """
        outpath = filedialog.asksaveasfilename()
        print("Saving as:", outpath)
        
        with open(outpath, "w+") as outfile:
            # create list of field names
            fieldnames = ['Camera_id', 'Directory',
                          'Image_Name', 'Date', 'Processed']
            for stat in STATS:
                for roi in ROI_TYPES:
                    fieldnames.append("_".join([roi, stat]))

            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            for img_name in self.images:
                # combine metadata and statistics
                output = self.images[img_name].metadata.copy()
                output.update(self.images[img_name].stats)
                output['Processed'] = (img_name in self.done)

                # write row
                writer.writerow(output)

    def load_session(self):
        inputpath = filedialog.askopenfilename()

        with open(inputpath) as infile:
            reader = csv.DictReader(infile)
            for i, row in enumerate(reader):
                img_dir = row['Directory']
                img_name = row['Image_Name']
                imfile = os.path.join(img_dir, img_name)
                img = myImage(imfile)

                self.images[img_name] = img
                for roi in ROI_TYPES:
                    self.images[img_name].coords[roi] = ast.literal_eval(
                        row["_".join([roi, "coord"])])
                        

                if i == 0:
                    self.curdir = img_dir

                if row['Processed'] == "True":
                    self.done[img_name] = True
                    self.curcoords = self.images[img_name].coords

    def quit(self):
        """ 
        Save workspace in a log file and close app
        """
        self.save()
        self.mw.destroy()

    def display_image(self, img_name=None):
        """ 
        display the current image
        """
        if img_name is not None:
            if self.curframe is not None:
                self.curframe.grid_remove()
            self.curframe = self.imageframes[img_name]
            self.curframe.grid(row=0, column=0)

            # update filelist
            self.filelist.clear_selection()
            self.filelist.select(img_name)

    def next_image(self):
        found = False
        for img_name in self.images:
            if found:
                self.display_image(img_name)
                return
            if img_name == self.curframe.image.name:
                found = True
                continue

    def finalize(self, img_name):
        self.done[img_name] = True
        """ 
        Mark image as processed and move to next image
        """
                
        # save coordinates
        self.curcoords = self.images[img_name].coords
        self.filelist.highlight(img_name)

        # next image
        self.next_image()
        
        # completely done
        if len(self.done) == len(self.images):
            self.quit()
    
    def clear_roi(self, img_name):
        """ 
        Clear roi of a myImage object and reset canvas
        """
        self.images[img_name].clear_roi()
        self.imageframes[img_name].canvas.delete("lines", "points")

    def prev_roi(self, img_name):
        """ 
        Copy ROI from previously finalized image
        """
        if self.curcoords is None:
            return
        self.clear_roi(img_name)
        self.images[img_name].coords = OrderedDict()
        
        for roi in ROI_TYPES:
            coord = list(self.curcoords[roi])
            self.images[img_name].coords[roi] = coord

        self.curframe.draw_polygons(self.images[img_name].coords)

    def create_gui(self, parent):
        # main window
        self.mw = parent
        h = self.mw.winfo_screenheight()
        w = self.mw.winfo_screenwidth()
        self.mw.geometry("%dx%d+0+0" % (w, h))

        # create save button
        save_button = tk.Button(
            self.mw, text="Save and close",
            command = lambda : self.quit())
        save_button.config(height=10, width=10)        
        save_button.grid(row=0, column=0, padx=10, sticky=tk.W+tk.E)

        # create controlbar
        controlbar = controlBar(self.mw, self)
        controlbar.grid(row=0, column=1, padx=10, sticky=tk.W+tk.E)
        
        # create filelist
        self.filelist = FileList(self.mw, self, self.images)
        self.filelist.grid(row=1, padx=10,
                           sticky=tk.N+tk.S)

        # populate listbox with files
        for img_name in self.images:
            self.filelist.listbox.insert(tk.END, img_name)
            if img_name in self.done:
                self.filelist.highlight(img_name)            

        # create main frame
        self.mainframe = tk.Frame(self.mw)
        self.mainframe.grid(row=1, column=1, padx=10, 
                            sticky=tk.N+tk.S+tk.W+tk.E)

        # create image frames
        self.imageframes = {}
        for i, img_name in enumerate(self.images):
            self.imageframes[img_name] = ImageFrame(self.mainframe,
                                                        self,
                                                        self.images[img_name])
            self.imageframes[img_name].draw_polygons(
                self.images[img_name].coords)
            if i == 0:
                self.display_image(img_name)

class FileList(tk.Frame):
    """
    Class for the file list.

    Parameters
    ----------
    MyImgs: List of MyImage objects
    """
    def __init__(self, parent, session, myImgs):
        self.session = session
        tk.Frame.__init__(self, parent)
        
        # create listbox widget
        self.scrollbar = ttk.Scrollbar(self)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = tk.Listbox(self, yscrollcommand=self.scrollbar.set,
                                  selectmode=tk.BROWSE, width=30)
        self.scrollbar.config(command=self.listbox.yview)
        self.listbox.pack(side=tk.LEFT, fill=tk.Y)

        # display the current selection
        self.listbox.bind(
            '<<ListboxSelect>>',
            lambda x: self.session.display_image(
                self.listbox.get(self.listbox.curselection()[0])))

    def select(self, img_name):
        for i, img_name2 in enumerate(self.session.images):
            if img_name == img_name2:
                self.listbox.selection_set(i)

    def highlight(self, img_name):
        for i, img_name2 in enumerate(self.session.images):
            if img_name == img_name2:
                self.listbox.itemconfig(i, {'bg':'green'})

    def clear_selection(self):
        self.listbox.selection_clear(0, tk.END)

class controlBar(tk.Frame):
    """
    Class for the control bar
    """
    def __init__(self, parent, session):
        self.session = session
        tk.Frame.__init__(self, parent)

        n_types = len(ROI_TYPES)

        clear_roi_button = tk.Button(
            self, text="Clear ROI",
            command = lambda: self.session.clear_roi(
                self.session.curframe.image.name))
        clear_roi_button.config(height=10, width=10)
        clear_roi_button.grid(row=0, column=0, rowspan=n_types, sticky=tk.W+tk.E)

        prev_roi_button = tk.Button(
            self, text="Apply\nPrevious\nROI",
            command= lambda: self.session.prev_roi(
                self.session.curframe.image.name))
        prev_roi_button.config(height=10, width=10)
        prev_roi_button.grid(row=0, column=1, rowspan=n_types, sticky=tk.W+tk.E)

        skip_img_button = tk.Button(
            self, text="Skip\nImage",
            command= lambda: self.session.next_image()
        )
        skip_img_button.config(height=10, width=10)
        skip_img_button.grid(row=0, column=2, rowspan=n_types, sticky=tk.W+tk.E)

        finalize_button = tk.Button(
            self, text="Finalize\nImage",
            command = lambda: self.session.finalize(
                self.session.curframe.image.name))
        finalize_button.config(height=10, width=10)
        finalize_button.grid(row=0, column=3, rowspan=n_types, sticky=tk.W+tk.E)

        # Radio option for ROI
        for i, roi in enumerate(ROI_TYPES):
            b = tk.Radiobutton(self, text=roi,
                               variable=self.session.roi, value=roi,
                               foreground=ROI_COLORS[roi]
            )
            b.grid(row=i, column=4)

class ImageFrame(tk.Frame):
    """
    Class to represent the image frame
    """
    def __init__(self, parent, session, myImg):
        self.session = session
        tk.Frame.__init__(self, parent)

        # variables
        self.image = myImg

        # create image frame
        image = Image.open(myImg.imfile)
        photo = ImageTk.PhotoImage(image)

        self.canvas = tk.Canvas(self, bg='white', height=image.size[1],
                           width=image.size[0])
        self.canvas.image = photo
        self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        self.canvas.pack()
        self.canvas.update()
        self.canvas.bind("<Button-1>", self.detect_coord)
        self.canvas.bind("<Button-3>",
                         lambda x: self.detect_coord(x, True))

    def detect_coord(self, event, final=False):
        # detect the coordinates of user click
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        roi = self.session.roi.get()

        if roi in ROI_TYPES:
            self.image.coords[roi].append((x, y))
            x0 = None
            y0 = None
            
            roi_len = len(self.image.coords[roi])
            if roi_len > 1:
                x0,y0 = self.image.coords[roi][-2]
            self.draw(x, y, x0, y0, roi)

            if final:
                x0,y0 = self.image.coords[roi][0]
                self.draw(x, y, x0, y0, roi, False)


    def draw(self, x, y, x0, y0, roi, point=True):
        # draw point
        if point:
            self.canvas.create_oval(x - 7, y - 7, x + 7, y + 7,
                                    fill=ROI_COLORS[roi],
                                    tags="points")

        # draw line
        if x0 is not None:
            self.canvas.create_line(x0, y0,
                                    x, y,
                                    fill=ROI_COLORS[roi],
                                    tags="lines"
                                    )

    def draw_polygons(self, coords):
        for roi in ROI_TYPES:
            if roi in coords:
                n = len(coords[roi])
                if len(coords[roi]) > 0:
                    x0, y0 = coords[roi][-1]
                    for i, coord in enumerate(coords[roi]):
                        x, y = coord
                        self.canvas.create_oval(x - 7, y - 7, x + 7, y + 7,
                                                fill=ROI_COLORS[roi],
                                                tags="points")
                        self.canvas.create_line(x0, y0,
                                                x, y,
                                                fill=ROI_COLORS[roi],
                                                tags="lines"
                                                )
                        x0, y0 = x, y

root = tk.Tk()
load = messagebox.askyesno("Load session", "Load output file?")
session = PhenoSession(root, load)
root.mainloop()
