"""Distance computing functionality between Neuron sections."""

import numpy as np

import bglibpy


class EuclideanSectionDistance:
    """Calculate euclidian distance between positions on two sections

    Parameters
    ----------

    hsection1 : hoc section
                First section
    hsection2 : hoc section
                Second section
    location1 : float
                range x along hsection1
    location2 : float
                range x along hsection2
    projection : string
                 planes to project on, e.g. 'xy'
    """
    # pylint: disable=invalid-name

    def __call__(
            self,
            hsection1=None,
            hsection2=None,
            location1=None,
            location2=None,
            projection=None,
    ):
        """Computes and returns the distance."""
        xs_interp1, ys_interp1, zs_interp1 = self.grindaway(hsection1)
        xs_interp2, ys_interp2, zs_interp2 = self.grindaway(hsection2)

        x1 = xs_interp1[int(np.floor((len(xs_interp1) - 1) * location1))]
        y1 = ys_interp1[int(np.floor((len(ys_interp1) - 1) * location1))]
        z1 = zs_interp1[int(np.floor((len(zs_interp1) - 1) * location1))]

        x2 = xs_interp2[int(np.floor((len(xs_interp2) - 1) * location2))]
        y2 = ys_interp2[int(np.floor((len(ys_interp2) - 1) * location2))]
        z2 = zs_interp2[int(np.floor((len(zs_interp2) - 1) * location2))]

        distance = 0
        if "x" in projection:
            distance += (x1 - x2) ** 2
        if "y" in projection:
            distance += (y1 - y2) ** 2
        if "z" in projection:
            distance += (z1 - z2) ** 2

        distance = np.sqrt(distance)

        return distance

    @staticmethod
    def grindaway(hsection):
        """Grindaway."""
        # get the data for the section
        n_segments = int(bglibpy.neuron.h.n3d(sec=hsection))
        n_comps = hsection.nseg

        xs = np.zeros(n_segments)
        ys = np.zeros(n_segments)
        zs = np.zeros(n_segments)
        lengths = np.zeros(n_segments)
        for index in range(n_segments):
            xs[index] = bglibpy.neuron.h.x3d(index, sec=hsection)
            ys[index] = bglibpy.neuron.h.y3d(index, sec=hsection)
            zs[index] = bglibpy.neuron.h.z3d(index, sec=hsection)
            lengths[index] = bglibpy.neuron.h.arc3d(index, sec=hsection)

        # to use Vector class's .interpolate()
        # must first scale the independent variable
        # i.e. normalize length along centroid
        lengths /= lengths[-1]

        # initialize the destination "independent" vector
        # range = np.array(n_comps+2)
        comp_range = np.arange(0, n_comps + 2) / n_comps - 1.0 / (2 * n_comps)
        comp_range[0] = 0
        comp_range[-1] = 1

        # length contains the normalized distances of the pt3d points
        # along the centroid of the section.  These are spaced at
        # irregular intervals.
        # range contains the normalized distances of the nodes along the
        # centroid of the section.  These are spaced at regular intervals.
        # Ready to interpolate.

        xs_interp = np.interp(comp_range, lengths, xs)
        ys_interp = np.interp(comp_range, lengths, ys)
        zs_interp = np.interp(comp_range, lengths, zs)

        return xs_interp, ys_interp, zs_interp