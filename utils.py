from PIL import Image, ImageTk, ImageDraw
import numpy as np
import os
from collections import OrderedDict
import exifread

ROI_TYPES = (
    "Overstory",
    "Understory",
    "In Between",
    "Openland",
)

ROI_COLORS = {
    "Overstory":"red",
    "Understory":"blue",
    "In Between":"black",
    "Openland":"green"
}

STATS = ("R", "G", "B", "VI", "coord")


class myImage(object):
    '''
    Represents and Image object.
    
    Parameters
    ----------
    imfile: path to the image file
    '''
    def __init__(self, imfile):
        # path variables
        self.imfile = imfile
        self.name = os.path.basename(imfile)
        self.directory = os.path.dirname(imfile)

        # ROI
        self.coords = OrderedDict()
        self.clear_roi()

    def clear_roi(self):
        """ clear coordinates for all ROI
        """
        for roi in ROI_TYPES:
            self.coords[roi] = []

    @property
    def stats(self):
        """ 
        calculate stats for each ROI
        
        returns
        ----------
        dict: dictionary with <ROI>_<STAT> as key
        """
        with Image.open(self.imfile) as img:
            stats = {}
            R,G,B = img.split()
            for roi in ROI_TYPES:
                # generate polygon from coordinates
                polygon = [tuple(coord) for coord in self.coords[roi]]
                
                # mask everything
                maskIm = Image.new('L', (R.width, R.height), 1) 
                if len(polygon) > 2:
                    # unmask region
                    ImageDraw.Draw(maskIm).polygon(polygon, outline=0, fill=0) 

                # channels masked with ROI
                R_masked = np.ma.array(R, mask=maskIm)
                G_masked = np.ma.array(G, mask=maskIm)
                B_masked = np.ma.array(B, mask=maskIm)

                # calculate statistics
                stats['_'.join([roi,'coord'])] = polygon
                if R_masked.count() != 0:
                    stats['_'.join([roi,'R'])] = R_masked.mean()
                    stats['_'.join([roi,'G'])] = G_masked.mean()
                    stats['_'.join([roi,'B'])] = B_masked.mean()
                    stats['_'.join([roi,'VI'])] = 2*G_masked.mean()-R_masked.mean()-B_masked.mean()
                else:
                    stats['_'.join([roi,'R'])] = None
                    stats['_'.join([roi,'G'])] = None
                    stats['_'.join([roi,'B'])] = None
                    stats['_'.join([roi,'VI'])] = None

            return(stats)

    @property
    def metadata(self):
        """
        Get method for the image metadata
        
        returns
        ----------
        dictionary of metadata
        """
        
        meta = {}
        meta['Directory'] = self.directory
        meta['Image_Name'] = self.name

        # TODO: code to set Camera_id and Date taken
        meta['Camera_id'] = None
        meta['Date'] = None

        return meta
