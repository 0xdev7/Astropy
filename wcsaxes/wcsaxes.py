import sys
import numpy as np

from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.transforms import Affine2D, Bbox

from astropy.wcs import WCS

from .transforms import (WCSPixel2WorldTransform, WCSWorld2PixelTransform,
                         CoordinateTransform)
from .grid_helpers import CoordinatesMap
from .utils import get_coordinate_system
from .coordinate_range import find_coordinate_range


class WCSAxes(Axes):

    def __init__(self, fig, rect, wcs=None, **kwargs):

        self.wcs = wcs

        super(WCSAxes, self).__init__(fig, rect, **kwargs)

        # Turn off spines and current axes

        for s in self.spines.values():
            s.set_visible(False)

        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)

        # Here determine all the coordinate axes that should be shown.

        self.coords = CoordinatesMap(self, self.wcs)

    def _get_bounding_frame(self):
        """
        Return the bounding frame of the axes.

        Returns
        -------
        bounding_frame : dict
            The bounding frame of the axes, as a dictionary containing
            different axes with different names. This allows the user to then
            specify which axis should contain ticks and labels.
        """

        xmin, xmax = self.get_xlim()
        ymin, ymax = self.get_ylim()

        frame = {}
        frame['b'] = ([xmin, xmax], [ymin, ymin])
        frame['r'] = ([xmax, xmax], [ymin, ymax])
        frame['t'] = ([xmax, xmin], [ymax, ymax])
        frame['l'] = ([xmin, xmin], [ymax, ymin])

        return frame

    def _sample_bounding_frame(self, n_samples):
        """
        Return n points equally spaced around the frame.

        Returns
        -------
        bounding_frame : dict
            The bounding frame of the axes, as a dictionary containing
            different axes with different names. This allows the user to then
            specify which axis should contain ticks and labels. The frame
            returns from this method is over-sampled.
        """
        frame = self._get_bounding_frame()
        new_frame = {}
        for axis in frame:
            x, y = frame[axis]
            p = np.linspace(0., 1., len(x))
            p_new = np.linspace(0., 1., n_samples)
            new_frame[axis] = np.interp(p_new, p, x), np.interp(p_new, p, y)
        return new_frame

    def get_coord_range(self):
        xmin, xmax = self.get_xlim()
        ymin, ymax = self.get_ylim()
        return find_coordinate_range(self.coords._transform.inverted(),
                                     [xmin, xmax, ymin, ymax],
                                     x_type=self.coords[0].coord_type,
                                     y_type=self.coords[1].coord_type)

    def draw(self, renderer, inframe=False):

        super(WCSAxes, self).draw(renderer, inframe)

        frame = self._get_bounding_frame()
        for axis in frame:
            x, y = frame[axis]
            line = Line2D(x, y, transform=self.transData, color='black')
            line.draw(renderer)

        # Here need to find out range of all coordinates, and update range for
        # each coordinate axis. For now, just assume it covers the whole sky.

        self.coords[0].draw(renderer)
        self.coords[1].draw(renderer)

    def get_transform(self, frame, equinox=None, obstime=None):

        if self.wcs is None and frame != 'pixel':
            raise ValueError('No WCS specified, so only pixel coordinates are available')

        if isinstance(frame, WCS):

            coord_in = get_coordinate_system(frame)
            coord_out = get_coordinate_system(self.wcs)

            if coord_in == coord_out:

                return (WCSPixel2WorldTransform(frame)
                        + WCSWorld2PixelTransform(self.wcs)
                        + self.transData)

            else:

                return (WCSPixel2WorldTransform(frame)
                        + CoordinateTransform(coord_in, coord_out)
                        + WCSWorld2PixelTransform(self.wcs)
                        + self.transData)

        elif frame == 'pixel':

            return Affine2D() + self.transData

        else:

            from astropy.coordinates import FK5, Galactic

            world2pixel = WCSWorld2PixelTransform(self.wcs) + self.transData

            if frame == 'world':

                return world2pixel

            elif frame == 'fk5':

                coord_class = get_coordinate_system(self.wcs)

                if coord_class is FK5:
                    return world2pixel
                else:
                    return (CoordinateTransform(FK5, coord_class)
                            + world2pixel)

            elif frame == 'galactic':

                coord_class = get_coordinate_system(self.wcs)

                if coord_class is Galactic:
                    return world2pixel
                else:
                    return (CoordinateTransform(Galactic, coord_class)
                            + world2pixel)

            else:

                raise NotImplemented("frame {0} not implemented".format(frame))

    def get_tightbbox(self, renderer):

        if not self.get_visible():
            return

        bb = []

        bb.extend(self.coords[0].ticklabels.bboxes)
        bb.extend(self.coords[1].ticklabels.bboxes)

        bb = [b for b in bb if b and (b.width!=0 or b.height!=0)]

        if bb:
            _bbox = Bbox.union(bb)
            return _bbox
        else:
            return None
