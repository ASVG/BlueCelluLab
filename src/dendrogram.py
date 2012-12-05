import pylab
import bglibpy
import numpy


class dendrogram:
    """Class that represent a dendrogram plot"""
    def __init__(self, sections, variable=None, active=False):
        pylab.ion()
        self.dend_figure = pylab.figure(figsize=(20, 12))
        pylab.ioff()

        self.sections = sections
        bglibpy.neuron.h.finitialize()

        self.hroot = bglibpy.neuron.h.SectionRef(sec=self.sections[0]).root
        self.proot = bglibpy.PSection(self.hroot, None)
        self.psections = [self.proot] + self.proot.getAllPDescendants()

        pylab.xlim([0, self.proot.treeWidth() + self.proot.ySpacing])
        pylab.ylim([0, self.proot.treeHeight() + self.proot.xSpacing])
        pylab.gca().set_xticks([])
        pylab.gca().set_yticks([])
        pylab.gcf().subplots_adjust(top=0.99, bottom=0.01, left=0.01, right=0.99, hspace=0.3)

        if variable is "v" or variable is None:
            varbounds = [-70, 50]
        else:
            varbounds = self.proot.getTreeVarBounds(variable)

        cax = pylab.imshow(numpy.outer(numpy.arange(0, 1, 0.1), numpy.ones(1)), aspect='auto', cmap=pylab.get_cmap("hot"), origin="lower")
        pylab.clim(varbounds[0], varbounds[1])

        cbar = self.dend_figure.colorbar(cax, ticks=[varbounds[0], varbounds[1]])
        cbar.ax.set_yticklabels(["%.2e" % (varbounds[0]), "%.2e" % (varbounds[1])])

        self.proot.drawTree(self.dend_figure, self.proot.ySpacing, self.proot.xSpacing, variable=variable, varbounds=varbounds)
        self.dend_figure.canvas.draw()

        for psection in self.psections:
            psection.redraw()

        self.canvas = self.dend_figure.gca().figure.canvas
        self.ax = self.dend_figure.gca()
        self.canvas.blit(self.ax.bbox)

        self.background = self.canvas.copy_from_bbox(self.dend_figure.gca().bbox)
        self.drawCount = 10

        self.active = active


def redraw(self):
        """Redraw the dendrogram"""
        if self.active:
            if not self.drawCount:
                for psection in self.psections:
                    psection.redraw()
                self.canvas.blit(self.ax.bbox)
                self.drawCount = 50
            else:

                self.drawCount = self.drawCount - 1

        return True