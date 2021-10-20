"""
Synapse test file. Uses ball-and-stick models
Models simulated in N disticnt ways, all shoudl
"""

# pylint: disable=E1101,W0201

import os
import numpy
import bglibpy

script_dir = os.path.dirname(__file__)

try:
    import greensFunctionCalculator as gfc
    gfc_imported = True
except ImportError:
    gfc_imported = False


class Params:

    """Simulation parameters"""

    def __init__(self):
        self.T_STOP = 200
        self.V_INIT = -75
        self.DT = 0.025

        self.SYN_DECAY = 2.0
        self.SYN_E = 0
        self.SYN_ACTIVATION_T = 50
        self.SYN_DELAY = 0.025
        self.SYN_G = 0.001
        self.SYN_LOC = 1.0

        self.templatefile = \
            "%s/examples/ballstick_cell/ballstick.hoc" % script_dir
        self.morphfile = \
            "%s/examples/ballstick_cell/ballstick.asc" % script_dir

        cell = bglibpy.Cell(self.templatefile, self.morphfile)
        self.soma_L, self.soma_D, self.soma_A = \
            cell.soma.L, cell.soma.diam, bglibpy.neuron.h.area(
                0.5, sec=cell.soma)
        # print 'SOMA L=%f, diam=%f,surf=%f' % (self.soma_L, self.soma_D,
        # self.soma_A)

        self.dend0_L, self.dend0_D, self.dend0_A = cell.basal[0].L, cell.basal[
            0].diam, bglibpy.neuron.h.area(
            0.5, sec=cell.basal[0])
        self.dend0_NSEG = cell.basal[0].nseg

        # print 'DENDRITE L=%f, diam=%f,surf=%f' % (self.dend0_L, self.dend0_D,
        # self.dend0_A)

        # I assume uniform passive properties shared by the soma and dendrites
        self.CM = cell.soma.cm
        self.RM = 1.0 / cell.soma(0.5).g_pas
        self.RA = cell.soma.Ra
        self.EL = cell.soma(0.5).e_pas

        self.d_derived = 10
        self.l_derived = self.soma_A / (2 * numpy.pi * self.d_derived / 2.0)


def run_pyneuron(soma_l, soma_d, params):
    """Run ballstick with PyNeuron"""
    soma = bglibpy.neuron.h.Section()
    soma.L = soma_l
    soma.diam = soma_d
    soma.nseg = 1
    soma.cm = params.CM
    soma.Ra = params.RA

    soma.insert('pas')
    soma(0.5).e_pas = params.EL
    soma(0.5).g_pas = 1.0 / params.RM

    dend = bglibpy.neuron.h.Section()
    dend.L = params.dend0_L
    dend.diam = params.dend0_D
    dend.nseg = params.dend0_NSEG

    dend.cm = params.CM
    dend.Ra = params.RA
    dend.insert('pas')
    for seg in dend:
        seg.e_pas = params.EL
        seg.g_pas = 1.0 / params.RM
    dend.connect(soma, 0.5, 0)  # mid-soma to begin-den

    syn = bglibpy.neuron.h.ExpSyn(params.SYN_LOC, sec=dend)
    syn.tau = params.SYN_DECAY
    syn.e = params.SYN_E

    ns = bglibpy.neuron.h.NetStim()
    ns.interval = 100000
    ns.number = 1
    ns.start = params.SYN_ACTIVATION_T
    ns.noise = 0

    nc = bglibpy.neuron.h.NetCon(ns, syn, 0, params.SYN_DELAY, params.SYN_G)

    v_vec = bglibpy.neuron.h.Vector()
    t_vec = bglibpy.neuron.h.Vector()
    v_vec.record(soma(0.5)._ref_v)
    t_vec.record(bglibpy.neuron.h._ref_t)

    bglibpy.neuron.h.finitialize(params.V_INIT)
    bglibpy.neuron.h.dt = params.DT
    bglibpy.neuron.run(params.T_STOP)

    voltage = numpy.array(v_vec)
    time = numpy.array(t_vec)

    del(syn)
    del(ns)
    del(nc)

    return time, voltage


def run_pyneuron_with_template(params):
    """Run ballstick with PyNeuron and template"""

    bglibpy.neuron.h.load_file(params.templatefile)
    cell = bglibpy.neuron.h.ballstick_cell(0, params.morphfile)
    basal = [x for x in cell.getCell().basal]
    soma = [x for x in cell.getCell().somatic][0]
    syn = bglibpy.neuron.h.ExpSyn(params.SYN_LOC, sec=basal[0])
    syn.tau = params.SYN_DECAY
    syn.e = params.SYN_E
    ns = bglibpy.neuron.h.NetStim()
    ns.interval = 100000
    ns.number = 1
    ns.start = params.SYN_ACTIVATION_T
    ns.noise = 0
    nc = bglibpy.neuron.h.NetCon(ns, syn, 0, params.SYN_DELAY, params.SYN_G)

    v_vec = bglibpy.neuron.h.Vector()
    t_vec = bglibpy.neuron.h.Vector()
    v_vec.record(soma(0.5)._ref_v)
    t_vec.record(bglibpy.neuron.h._ref_t)

    bglibpy.neuron.h.finitialize(params.V_INIT)
    bglibpy.neuron.h.dt = params.DT
    bglibpy.neuron.run(params.T_STOP)

    voltage = numpy.array(v_vec)
    time = numpy.array(t_vec)

    cell.getCell().clear()

    del(syn)
    del(ns)
    del(nc)
    del(cell)

    return time, voltage


def run_bglibpy(params):
    """Run ballstick with BGLibPy"""
    cell = bglibpy.Cell(params.templatefile, params.morphfile)
    syn = bglibpy.neuron.h.ExpSyn(params.SYN_LOC, sec=cell.basal[0])
    syn.tau = params.SYN_DECAY
    syn.e = params.SYN_E
    ns = bglibpy.neuron.h.NetStim()
    ns.interval = 100000
    ns.number = 1
    ns.start = params.SYN_ACTIVATION_T
    ns.noise = 0
    nc = bglibpy.neuron.h.NetCon(ns, syn, 0, params.SYN_DELAY, params.SYN_G)

    sim = bglibpy.Simulation()
    sim.add_cell(cell)
    sim.run(params.T_STOP, v_init=params.V_INIT, cvode=False, dt=params.DT)
    bglibpy_t = cell.get_time()
    bglibpy_v = cell.get_soma_voltage()

    del(sim)
    del(syn)
    del(ns)
    del(nc)
    del(cell)

    return bglibpy_t, bglibpy_v


def run_analytic(params):
    ''' write config file for Willem '''
    f_name = '%s/examples/ballstick_cell/bs.cfg' % script_dir
    outF = open(f_name, 'w')
    outF.write('[neuron]\n')
    outF.write('CM: %f\n' % (params.CM))
    outF.write('RM: %f\n' % (params.RM))
    outF.write('RA: %f\n' % (params.RA))
    outF.write('EL: %f\n\n' % (params.EL))
    outF.write('[soma]\n')
    outF.write('D: ' + str(params.d_derived) + '\n')
    outF.write('L: ' + str(params.l_derived) + '\n\n')
    outF.write('[morph]\n')
    outF.write('lengths: [%f]\n' % (params.dend0_L))
    outF.write('diams: [%f]\n' % (params.dend0_D))
    outF.close()

    v_willem, t_willem = gfc.compute_system(
        [[params.SYN_ACTIVATION_T]], params.T_STOP, params.DT,
        conffile_name=f_name, numsyn=1, syndend=[0], synloc=[params.SYN_LOC],
        gbar=[params.SYN_G], decay=[params.SYN_DECAY], E_rev=[params.SYN_E])
    return t_willem, v_willem


def test_expsyn_pyneuron_vs_bglibpy(graph=False):
    """Ballstick: Test ballstick with expsyn between pyneuron and bglibpy"""

    """
    The real stuff, part I
    Run the ball-and-stick model by 1. PyNEURON, 2. bglibpy, 3. analytic
    """

    params = Params()  # define all the parameters

    # Run in pure PyNeuron, with using the template
    pyneuron_t, pyneuron_v = run_pyneuron(
        params.l_derived, params.d_derived, params)

    # Run with template in PyNeuron
    pyneuron_template_t, pyneuron_template_v = run_pyneuron_with_template(
        params)

    # Run with BGLibPy
    bglibpy_t, bglibpy_v = run_bglibpy(params)

    # Run with analytic solution
    analytic_expsyn_path = \
        "%s/examples/ballstick_cell/analytic_expsyn.txt" % script_dir

    if gfc_imported:
        analytic_t, analytic_v = run_analytic(params)
        numpy.savetxt(analytic_expsyn_path, (analytic_t, analytic_v))
    else:
        analytic_t, analytic_v = numpy.loadtxt(analytic_expsyn_path)

    assert len(analytic_v) == 8000
    pyneuron_rms_error = numpy.sqrt(
        numpy.mean(
            (analytic_v -
             pyneuron_v[
                 :len(analytic_v)]) ** 2))
    pyneuron_template_rms_error = numpy.sqrt(
        numpy.mean(
            (analytic_v -
             pyneuron_template_v[
                 :len(analytic_v)]) ** 2))
    bglibpy_rms_error = numpy.sqrt(
        numpy.mean(
            (analytic_v -
             bglibpy_v[
                 :len(analytic_v)]) ** 2))
    assert pyneuron_rms_error < 0.1
    assert pyneuron_template_rms_error < 0.1
    assert bglibpy_rms_error < 0.1

    if graph:
        import pylab
        pylab.plot(bglibpy_t, bglibpy_v, 'g', label='BGLibPy')
        pylab.plot(pyneuron_t, pyneuron_v, 'b', label='PyNeuron')
        pylab.plot(
            pyneuron_template_t,
            pyneuron_template_v,
            'r',
            label='PyNeuron with template')
        pylab.plot(analytic_t, analytic_v, 'o-', label='Analytic')
        pylab.legend(loc=0)
        pylab.show()


def test_ballstick_load():
    """Ballstick: Test if dimensions of ballstick load correctly"""
    params = Params()

    cell = bglibpy.Cell(params.templatefile, params.morphfile)
    assert abs(cell.soma.L - 19.6) < 0.001
    assert abs(cell.soma.diam - 10.229) < 0.001
    assert abs(bglibpy.neuron.h.area(0.5, sec=cell.soma) - 872.567) < 0.001
    assert abs(cell.basal[0].L - 200.0) < 0.001
    assert abs(cell.basal[0].diam - 3.0) < 0.001
    assert abs(bglibpy.neuron.h.area(0.5, sec=cell.basal[0]) - 9.424) < 0.001

    del cell


def main():
    """main"""
    test_expsyn_pyneuron_vs_bglibpy(graph=True)


if __name__ == "__main__":
    main()