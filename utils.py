from PIL import Image, ImageTk, ImageDraw
import numpy as np
import os
from collections import OrderedDict
from PIL.ExifTags import TAGS


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

CANVAS_SIZE = {
    "width":1600,
    "height":1200,
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
        self.camera_id = ""
        self.date

        # ROI
        self.coords = OrderedDict()
        self.new_ROI = False # True: if detect point; False: if clear_ROI
        self.clear_roi()

    def clear_roi(self):
        """ clear coordinates for all ROI
        """
        for roi in ROI_TYPES:
            self.coords[roi] = []
        self.new_ROI = False

    @property
    def date(self):
        if hasattr(self, "_date"):
            return self._date
        img = Image.open(self.imfile)
        info = img._getexif()
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "DateTimeOriginal":
                date = value
                break
        img.close()
        self._date = date
        return date

    @property
    def stats(self):
        """ 
        calculate stats for each ROI
        
        returns
        ----------
        dict: dictionary with <ROI>_<STAT> as key
        """
        with Image.open(self.imfile) as img:
            R,G,B = img.split()
            stats = {
                'overall_R':np.array(R).mean(),
                'overall_G':np.array(G).mean(),
                'overall_B':np.array(B).mean()
            }

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
            stats["new_ROI"] = self.new_ROI
            return(stats)

    @property
    def metadata(self):
        """
        Get method for the image metadata
        
        returns
        ----------
        dictionary of metadata
        """
        if hasattr(self, "_metadata"):
            self._metadata['Camera_id'] = self.camera_id
            return self._metadata
        meta = {}
        meta['Directory'] = self.directory
        meta['Image_Name'] = self.name

        # TODO: code to set Camera_id and Date taken
        meta['Camera_id'] = self.camera_id
        meta["Date"] = self.date

        self._metadata = meta
        return meta


def main():
    ''' for debugging '''
    directory = '/home/younghoon/data/phenology/BROW022/00430/20161028141801'
    imfiles = [os.path.join(directory, f) for f in os.listdir(directory)]

    for imfile in imfiles:
        img = myImage(imfile)
        pass

if __name__=="__main__":
    main()
