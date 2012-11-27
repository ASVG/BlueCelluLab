"""
Python library for running single cell bglib templates
"""

import sys
import os
import inspect
import pickle

os.environ['HOC_LIBRARY_PATH'] = "/home/torben/work/epfl/projects/bglib1.5/lib/hoclib:/home/torben/work/epfl/projects/bglib1.5/lib/hoclib/alib"#"/home/vangeit/src/bglib1.5/lib/hoclib"

import numpy
import re
import matplotlib as plt
import pylab
import multiprocessing
import math
import itertools

installdir = os.path.dirname(__file__)
pathsconfig_filename = installdir+"/paths.config"

if os.path.exists(pathsconfig_filename):
    pathsconfig = {line.strip().split("=")[0]: line.strip().split("=")[1] for line in open(pathsconfig_filename, "r")}
else:
    raise Exception("Sorry, can not find the file paths.config")

os.environ["HOC_LIBRARY_PATH"] = pathsconfig["HOC_LIBRARY_PATH"]

sys.path = [pathsconfig["NRNPYTHONPATH"]]  + sys.path
import neuron
neuron.h.nrn_load_dll(pathsconfig["NRNMECH_PATH"])
neuron.h.load_file("nrngui.hoc")
import collections

import bluepy
from bluepy.targets.mvddb import MType
from bluepy.targets.mvddb import Neuron

#tmpstdout = os.dup(1)
#tmpstderr = os.dup(2)
#devnull = os.open('/dev/null', os.O_WRONLY)
#os.dup2(devnull, 1)
#os.dup2(devnull, 2)
#os.close(devnull)
#sys.path = ["/usr/local/nrnnogui/lib/python2.7/site-packages"]  + sys.path
#sys.path = ["/home/torben/local/lib/python2.7/site-packages"]  + sys.path
#import neuron
#neuron.h.nrn_load_dll('/home/torben/work/epfl/projects/bglibpy/x86_64/.libs/libnrnmech.so')

#neuron.h.load_file("stdrun.hoc")
#neuron.h.load_file("TStim.hoc")
#neuron.h.load_file("nrngui.hoc") # I prefer not using the gui

#os.dup2(tmpstdout, 1)
#os.dup2(tmpstderr, 2)

# load some BGLIB stuff
neuron.h.load_file("Cell.hoc")
neuron.h.load_file("TDistFunc.hoc")

neuron.h.load_file("SerializedCell.hoc")
neuron.h('obfunc new_IClamp() { return new IClamp($1) }')

BLUECONFIG_KEYWORDS = ['Run', 'Stimulus', 'StimulusInject', 'Report', 'Connection']

def _me() : print 'Call -> from %s::%s' % (inspect.stack()[1][1], inspect.stack()[1][3])

def load_nrnmechanisms(libnrnmech_location):
    """Load another shared library with neuron mechanisms"""
    neuron.h.nrn_load_dll(libnrnmech_location)

def parse_complete_BlueConfig(fName) :
    """ Simplistic parser of the BlueConfig file """
    bc = open(fName,'r')
    uber_hash = {}#collections.OrderedDict
    for keyword in BLUECONFIG_KEYWORDS :
        uber_hash[keyword] = {}
    line = bc.next()

    while(line != '') :
        stripped_line = line.strip()
        if(stripped_line.startswith('#')) :
            ''' continue to next line '''
            line = bc.next()
        elif(stripped_line == '') :
            # print 'found empty line'
            try :
                line = bc.next()
            except StopIteration :
                # print 'I think i am at the end of the file'
                break
        elif(stripped_line.split()[0].strip() in BLUECONFIG_KEYWORDS ) :
            key = stripped_line.split()[0].strip()
            value = stripped_line.split()[1].strip()
            # print 'came accross key >',key,'<, value: >',value,'<'
            # parse the entries in that block
            parsed_dict = _parse_block_statement(bc)
            # add to the correct uber-dictionary
            uber_hash[key][value] = parsed_dict
            # print 'came accross key >',key,'<, value: >',value,'<'
            # print 'added the following dict:\n',parsed_dict
            line = bc.next()
        else :
            line = bc.next()
    return uber_hash

def _parse_block_statement(file_object) :
    ''' parse the content of the blocks in BlueConfig'''
    file_object.next() # skip the opening "}"
    line = file_object.next().strip()
    ret_dict = {}
    while(not line.startswith('}')) :
        # print '_parse_block_statement, line: >',line,'<'
        if(len(line) == 0 or line.startswith('#')) :
            line = file_object.next().strip()
        else :
            key = line.split(' ')[0].strip()
            values = line.split(' ')[1:]
            for value in values :
                if(value == '') :
                    pass
                else :
                    ret_dict[key] = value
                # print '_parse_block... stored [',key,']: >', value,'<'
            line = file_object.next().strip()
        # raw_input('press ENTER')
    # print 'line after the }, returning: ', ret_dict
    return ret_dict

def parse_paths_BlueConfig(fName) :
    """ Parse the main paths defined in the BlueConfig file """
    bc = open(fName,'r')
    return_object = {}
    for line in bc.readlines() :
        stripped_line = line.strip()
        if(stripped_line.startswith('Prefix')) :
            return_object['prefix'] = stripped_line.split()[1]
        elif(stripped_line.startswith('MorphologyPath')) :
            return_object['morphology_path'] = stripped_line.split()[1]
        elif(stripped_line.startswith('METypePath')) :
            return_object['me_type_path'] = stripped_line.split()[1]
        elif(stripped_line.startswith('CircuitPath')) :
            return_object['circuit_path'] = stripped_line.split()[1]
        elif(stripped_line.startswith('nrnPath')) :
            return_object['nrn_path'] = stripped_line.split()[1]

            return_object['main_path'] = fName[:-10] # stripped the "BlueConfig"
    return return_object

def parse_and_store_GID_spiketrains(path,fName='out.dat',store=False) :
    xhashed = {}
    inFile = open(path + '/' + fName,'r')
    inLine = inFile.readline()
    inLine = inFile.readline() # avoid the trailing "/scatter"
    counter = 0
    all_gids = []
    while(inLine != None) :
        try :
            # format: time gid
            t,gid = inLine.split() # returns 2 strings
            t = float(t)
            igid = int(gid)
            all_gids.append(igid)
            if(igid in xhashed) :
                xhashed[igid].append(t)
            else :
                xhashed[igid] = []
                xhashed[igid].append(t)
            counter = counter + 1
            inLine = inFile.readline()
        except :
            print 'no issue, most likely the last entry'
            print 'current inLine: ', inLine
            print 'current counter: ', counter
            inLine = inFile.readline()
            break

    print 'read and stored all spikes. now going to write the output'
    if not os.path.exists('presynaptic_temp'): os.makedirs('presynaptic_temp')

    if(store) :
        for key in xhashed.keys() :
            fN = 'presynaptic_temp/' +str(key) + '_spikes.dat'
            #print 'fn >%s<' % fN
            outF = open(fN,'w')
            outF.write( '\t'.join(map(str, xhashed[key]))  )
            outF.flush()
            outF.close()
    return xhashed

def _get_template_name_of_gid(bg_dict,cell_gid) :
    ncs_file = open(bg_dict['Run']['Default']['nrnPath']+'/start.ncs')
    template_name = None
    for line in ncs_file.readlines() :
        stripped_line = line.strip()

        #if(stripped_line.startswith('a'+str(cell_gid))) :
        try :
            if( int(stripped_line.split(' ')[0][1:]) == cell_gid) :
                template_name = line.split()[4]
                print stripped_line
        except :
            pass
    return template_name

def recreate_bare_gid(blue_config_filename,cell_gid) :
    bg_dict = parse_complete_BlueConfig(blue_config_filename)
    bp_simulation = bluepy.Simulation(blue_config_filename)

    ''' fetch the template for this GID, stored in template_name '''
    template_name = _get_template_name_of_gid(bg_dict,cell_gid)
    if(template_name == None) :
        _me()
        print 'i could not find the template. terminating replay'
        return

    ''' fetch synapse details '''
    pre_gids = bp_simulation.circuit.get_presynaptic_gids(cell_gid)
    pre_datas = bp_simulation.circuit.get_presynaptic_data(cell_gid)

    ''' parse incoming spike data'''
    pre_spike_trains = parse_and_store_GID_spiketrains(bg_dict['Run']['Default']['OutputRoot'],'out.dat',store=False)

    ''' construct the model neuron '''
    full_template_name = bg_dict['Run']['Default']['METypePath']+'/'+template_name + '.hoc'
    path_of_morphology =  bg_dict['Run']['Default']['MorphologyPath'] + '/ascii'
    model = Cell(full_template_name,path_of_morphology)

    ''' add the synapses to the model'''
    counter = 0
    synapse_distances = []
    for syn_description in pre_datas :
        spiketrain = []
        if(counter == -1) : # a bit pointless, no: i never wantthe spiketrains here. so just remove the if statement
            spiketrain = pre_spike_trains[int(syn_description[0])]
        distance = model.add_replay_synapse(syn_description,spiketrain,SID=counter,TGID=cell_gid,spontMiniRate=0,nmda_ratio=0,test=0)
        synapse_distances.append(distance)
        counter = counter  +1
    print 'added synapses: %i' % (counter)

    return model,synapse_distances

def recreate_one_gid(blue_config_filename, cell_gid,without_pre_spikes=False) :
    bg_dict = parse_complete_BlueConfig(blue_config_filename)
    bp_simulation = bluepy.Simulation(blue_config_filename)

    ''' fetch the template for this GID, stored in template_name '''
    template_name = _get_template_name_of_gid(bg_dict,cell_gid)
    if(template_name == None) :
        _me()
        print 'i could not find the template. terminating replay'
        return

    ''' fetch synapse details '''
    pre_gids = bp_simulation.circuit.get_presynaptic_gids(cell_gid)
    pre_datas = bp_simulation.circuit.get_presynaptic_data(cell_gid)

    ''' parse incoming spike data'''
    pre_spike_trains = parse_and_store_GID_spiketrains(bg_dict['Run']['Default']['OutputRoot'],'out.dat',store=False)

    ''' construct the model neuron '''
    full_template_name = bg_dict['Run']['Default']['METypePath']+'/'+template_name + '.hoc'
    path_of_morphology =  bg_dict['Run']['Default']['MorphologyPath'] + '/ascii'
    model = Cell(full_template_name,path_of_morphology)

    ''' add the synapses to the model'''
    counter = 0
    no_input_synapses = 0
    for syn_description in pre_datas :
        spiketrain = []
        try :
            if(without_pre_spikes) :
                spiketrain = [] #pre_spike_trains[int(syn_description[0])]
            else :
                spiketrain = pre_spike_trains[int(syn_description[0])]
            # fN = 'presynaptic_temp/' +str(pre_gid) + '_spikes.dat'
            # spiketrain = list(scipy.loadtxt(fN))
            # print 'spiketrain: ', spiketrain
        except Exception:
            no_input_synapses = no_input_synapses + 1
            model.add_replay_synapse(syn_description,spiketrain,SID=counter,TGID=cell_gid,spontMiniRate=0.04,nmda_ratio=0.4,test=0)
        counter = counter + 1
    print 'processed %f synapses of which %f DO NOT receive a spiketrain' % (counter,no_input_synapses)

    return model

def imprecise_replay(blue_config_filename, cell_gid,t_stop=1000,dt=0.025) :
    bg_dict = parse_complete_BlueConfig(blue_config_filename)
    bp_simulation = bluepy.Simulation(blue_config_filename)

    ''' fetch the template for this GID, stored in template_name '''
    template_name = _get_template_name_of_gid(bg_dict,cell_gid)
    if(template_name == None) :
        _me()
        print 'i could not find the template. terminating replay'
        return

    ''' fetch synapse details '''
    pre_gids = bp_simulation.circuit.get_presynaptic_gids(cell_gid)
    pre_datas = bp_simulation.circuit.get_presynaptic_data(cell_gid)

    ''' parse incoming spike data'''
    pre_spike_trains = parse_and_store_GID_spiketrains(bg_dict['Run']['Default']['OutputRoot'],'out.dat',store=False)

    ''' construct the model neuron '''
    full_template_name = bg_dict['Run']['Default']['METypePath']+'/'+template_name + '.hoc'
    path_of_morphology =  bg_dict['Run']['Default']['MorphologyPath'] + '/ascii'
    model = Cell(full_template_name,path_of_morphology)

    ''' add the synapses to the model'''
    counter = 0
    no_input_synapses = 0
    for syn_description in pre_datas :
        spiketrain = []
        try :
            spiketrain = pre_spike_trains[int(syn_description[0])]
            # fN = 'presynaptic_temp/' +str(pre_gid) + '_spikes.dat'
            # spiketrain = list(scipy.loadtxt(fN))
            # print 'spiketrain: ', spiketrain
        except Exception:
            no_input_synapses = no_input_synapses + 1
        model.add_replay_synapse(syn_description,spiketrain,SID=counter,TGID=cell_gid,spontMiniRate=0.04,nmda_ratio=0.4,test=0)
        counter = counter + 1
    print 'processed %f synapses of which %f DO NOT receive a spiketrain' % (counter,no_input_synapses)

    # THE FOLLOWING HAS TO BE SET HY HAND (at this moment)
    model.add_replay_noise(cell_gid,1.2 * model.getThreshold(), 0.001*model.getThreshold()/100.0,0)
    hypamp_i =1.0 * model.getHypAmp() #cell.getCell().getThreshold()
    model.addRamp(0,10000,hypamp_i,hypamp_i,dt=0.025)

    ''' RUN '''
    simulation = Simulation()
    simulation.addCell(model)
    simulation.run(t_stop,cvode=False,dt=dt)
    time = model.getTime()
    voltage = model.getSomaVoltage()

    pickle.dump([time,voltage],open(str(cell_gid)+'_imprecise_replay_'+str(t_stop)+'.pkl','w'))
    return time,voltage

class Cell:
    """Represents a bglib cell"""

    class persistent:
        """The objects that need to stay persistent in python"""
        objects = []


    def __init__(self, template_name, morphology_name):
        neuron.h.load_file(template_name)
        template_content = open(template_name, "r").read()
        match = re.search("begintemplate\s*(\S*)", template_content)
        cell_name = match.group(1)
        self.cell = eval("neuron.h."+ cell_name +"(0, morphology_name)")
        self.recordings = {}
        self.synapses = {}
        self.netstims = {}
        self.connections = {}

        self.mechanisms = [] # BTN: all additional mechanism stored in one list. easy to delete...

        self.synapse_number = 0
        self.syn_vecs = {}
        self.syn_vecstims ={}
        self.syns = {}
        self.syn_netcons = {}
        self.ips = {}
        self.syn_mini_netcons = {}


        #neuron.h('objref serialized')
        #neuron.h.serialized = neuron.h.SerializedSections(self.cell.getCell())#CellRef)
        self.serialized = neuron.h.SerializedSections(self.cell.getCell())
        neuron.h.finitialize()

        self.soma = [x for x in self.cell.getCell().somatic][0]
        self.somatic = [x for x in self.cell.getCell().somatic]
        self.basal = [x for x in self.cell.getCell().basal]
        self.apical = [x for x in self.cell.getCell().apical]
        self.axonal = [x for x in self.cell.getCell().axonal]
        self.all = [x for x in self.cell.getCell().all]

        self.addRecordings(['self.soma(0.5)._ref_v', 'neuron.h._ref_t'])
        self.cell_dendrograms = []
        self.plotWindows = []


    def re_init_rng(self):
        """Reinitialize the random number generator for the stochastic channels"""
        self.cell.re_init_rng()
        neuron.h.finitialize()

    def get_section(self,raw_section_id) :
        ''' use the serialized object to find your section'''
        return self.serialized.isec2sec[int(raw_section_id)].sec

    def location_to_point(self,syn_description,test=False) :
        pre_gid =  syn_description[0]
        post_sec_id = syn_description[2]
        isec = post_sec_id
        post_seg_id = syn_description[3]
        ipt = post_seg_id
        post_seg_distance = syn_description[4]
        syn_offset = post_seg_distance

        curr_sec = self.get_section(post_sec_id)
        L = curr_sec.L

        debug_too_large = 0
        debug_too_small = 0
        # access section to compute the distance
        if( neuron.h.section_orientation(sec=self.get_section(isec)) == 1) :
            ipt = neuron.h.n3d(sec=self.get_section(isec)) -1 - ipt

        if(ipt < neuron.h.n3d(sec=self.get_section(isec)) ) :
            distance = (ipt+syn_offset)/L
            if(distance >= 1.0) :
                distance = 1
                debug_too_large = debug_too_large + 1

        if( neuron.h.section_orientation(sec=self.get_section(isec)) == 1  ) :
            distance = 1 - distance

        if(distance <=0 ) :
            distance =0
            debug_too_small = debug_too_small + 1

        if(test) :
            print 'location_to_point:: %i <=0 and %i >= 1' % (debug_too_small,debug_too_large)

        return distance


    def getThreshold(self):
        """Get the spiking threshold of the cell"""
        return self.cell.getThreshold()


    def getHypAmp(self):
        """Get the current level necessary to bring the cell to -85 mV"""
        return self.cell.getHypAmp()


    def showDendDiam(self):
        """Show a dendrogram plot"""
        diamlist = [section.diam for section in self.apical]
        pylab.hist(diamlist, bins=int((max(diamlist)-min(diamlist))/.1))
        pylab.show()


    def addRecording(self, var_name):
        """Add a recording to the cell"""
        #soma = [x for x in self.cell.getCell().somatic][0]
        #soma = soma
        recording = neuron.h.Vector()
        recording.record(eval(var_name))
        self.recordings[var_name] = recording

    def addRecordings(self, var_names):
        """Add a set of recordings to the cell"""
        for var_name in var_names:
            self.addRecording(var_name)


    def addAllSectionsVoltageRecordings(self):
        """Add a voltage recording to every section of the cell"""
        all_sections = self.cell.getCell().all
        for section in all_sections:
            var_name = 'neuron.h.' + section.name() + "(0.5)._ref_v"
            self.addRecording(var_name)


    def getAllSectionsVoltageRecordings(self):
        """Get all the voltage recordings from all the sections"""
        allSectionVoltages = {}
        all_sections = self.cell.getCell().all
        for section in all_sections:
            var_name = 'neuron.h.' + section.name() + "(0.5)._ref_v"
            allSectionVoltages[section.name()] = self.getRecording(var_name)
        return allSectionVoltages


    def getRecording(self, var_name):
        """Get recorded values"""
        return self.recordings[var_name].to_python()

    def add_replay_noise(self,gid,mean,variance,noise_seed,delay=0,dur=10000) :
        rand = neuron.h.Random(gid+noise_seed)
        tstim =neuron.h.TStim(0.5, rand, sec=self.soma)# self.get_section(0)) # assuming that section 0 is the soma
        tstim.noise(delay, dur, mean, variance)
        self.mechanisms.append(rand)
        self.mechanisms.append(tstim)

    def add_replay_synapse(self,syn_description,spike_train,SID=1,TGID=1,baseSeed=0,weightScalar=1.0,spontMiniRate=0.0,nmda_ratio=-66,e_gaba=-80,dt=0.025,test=False) :
        ''' Adds synapses the way BGLib does is. Supposedly.'''
        pre_gid =  syn_description[0]
        delay = syn_description[1]
        post_sec_id = syn_description[2]
        post_seg_id = syn_description[3]
        post_seg_distance = syn_description[4]
        gsyn = syn_description[8]
        syn_U = syn_description[9]
        syn_D = syn_description[10]
        syn_F = syn_description[11]
        syn_DTC = syn_description[12]
        syn_type = syn_description[13]
        syn_pre_m_type = syn_description[14]
        syn_ASE = syn_description[17]

        ''' set up the vecevent thing '''
        t_vec = neuron.h.Vector(spike_train)
        t_vec_stim = neuron.h.VecStim()
        self.syn_vecs[SID] = t_vec
        self.syn_vecstims[SID] = t_vec_stim
        self.syn_vecstims[SID].play(self.syn_vecs[SID],dt)

        location = self.location_to_point(syn_description,test=test)
        distance =  neuron.h.distance(location, sec=self.get_section(post_sec_id))
        if(syn_type < 100) :
            ''' see: https://bbpteam.epfl.ch/wiki/index.php/BlueBuilder_Specifications#NRN,'''
            ''' inhibitory synapse '''
            if(test) :
                print 'Inserting synapse in %i(%f)' % (post_sec_id,location)
            syn = neuron.h.ProbGABAAB_EMS(location,sec=self.get_section(post_sec_id))
            syn.e_GABAA = e_gaba
            syn.tau_d_GABAA = syn_DTC
            rng = neuron.h.Random()
            rng.MCellRan4(SID *100000+100,TGID+250+baseSeed) # +0 is the baseSeed, what's baseSeed?
            rng.lognormal(0.2,0.1)
            syn.tau_r_GABAA = rng.repick()
        else :
            ''' else we have excitatory synapse '''
            syn = neuron.h.ProbAMPANMDA_EMS(location,sec=self.get_section(post_sec_id))
            syn.tau_d_AMPA = syn_DTC
            if(nmda_ratio != -66) :
                syn.NMDA_ratio=nmda_ratio

        syn.Use = abs( syn_U )
        syn.Dep = abs( syn_D )
        syn.Fac = abs( syn_F )
        syn.synapseID=SID

        rndd = neuron.h.Random()
        rndd.MCellRan4(SID*100000+100, TGID+250+baseSeed )
        rndd.uniform(0,1)
        syn.setRNG(rndd)
        self.mechanisms.append(rndd)

        # self.mechanisms.append(syn)
        self.syns[SID] = syn

        self.syn_netcons[SID] = neuron.h.NetCon(self.syn_vecstims[SID],self.syns[SID],-30,delay,gsyn*weightScalar) # ...,threshold,delay,weight

        ''' add the *minis*: spontaneous synaptic events '''
        if(spontMiniRate > 0.0) :
            self.ips[SID] = neuron.h.InhPoissonStim(location,sec=self.get_section(post_sec_id))

            self.syn_mini_netcons[SID] = neuron.h.NetCon(self.ips[SID],self.syns[SID],-30,0.1,gsyn*weightScalar) # delay=0.1, fixed in Connection.hoc

            exprng = neuron.h.Random()
            exprng.MCellRan4( SID*100000+200, TGID+250+baseSeed )
            exprng.negexp(1)
            self.mechanisms.append(exprng)
            uniformrng = neuron.h.Random()
            uniformrng.MCellRan4( SID*100000+300, TGID+250+baseSeed )
            uniformrng.uniform(0.0,1.0)
            self.mechanisms.append(uniformrng)
            self.ips[SID].setRNGs(exprng, uniformrng)
            tbins_vec = neuron.h.Vector(1)
            tbins_vec.x[0] = 0.0
            rate_vec = neuron.h.Vector(1)
            if(spontMiniRate == 0) :
                rate_vec.x[0] = spontMiniRate # hack to set ALL the spont mini rates to 0
            else :
                rate_vec.x[0] = spontMiniRate if(syn_type >=100) else  0.012 # according to Blueconfig, ConInh-uni rule
            self.mechanisms.append(tbins_vec)
            self.mechanisms.append(rate_vec)
            self.ips[SID].setTbins(tbins_vec)
            self.ips[SID].setRate(rate_vec)

        return distance

    def addSynapticStimulus(self, section, location, delay=150, gmax=.000000002):
        """Add a synaptic stimulus to a certain section"""
        segname = section.name() + "(" + str(location) + ")"
        synapse = neuron.h.tmgExSyn(location, sec=section)
        synapse.Use = 0.5
        synapse.Fac = 21

        netstim = neuron.h.NetStim(sec=section)
        stimfreq = 70
        netstim.interval = 1000/stimfreq
        netstim.number = 1
        netstim.start = delay
        netstim.noise = 0
        connection = neuron.h.NetCon(netstim, synapse, 10, 0, 700, sec=section)
        connection.weight[0] = 1.0
        self.synapses[segname] = synapse
        self.netstims[segname] = netstim
        self.connections[segname] = connection


    def locateBAPSite(self, seclistName, distance):
        """Return the location of the BAP site"""
        return [x for x in self.cell.getCell().locateBAPSite(seclistName, distance)]


    def removeSynapticStimulus(self, segname):
        """Removed a synaptic stimulus"""
        self.synapses[segname] = None
        self.netstims[segname] = None
        self.connections[segname] = None


    def addAllSynapses(self):
        """Add synapses to all dendritic sections"""
        dendritic_sections = [x for x in self.cell.getCell().basal] + [x for x in self.cell.getCell().apical]
        for section in dendritic_sections:
            self.addSynapticStimulus(section, 0)
            self.addSynapticStimulus(section, 0.5)
            self.addSynapticStimulus(section, 1)


    def injectCurrentWaveform(self, t_content, i_content):
        """Inject a current in the cell"""
        start_time = t_content[0]
        stop_time = t_content[-1]
        time = neuron.h.Vector()
        currents = neuron.h.Vector()
        time = time.from_python(t_content)
        currents = currents.from_python(i_content)

        pulse = neuron.h.new_IClamp(0.5, sec=self.soma)
        self.persistent.objects.append(pulse)
        self.persistent.objects.append(time)
        self.persistent.objects.append(currents)
        setattr(pulse, 'del', start_time)
        pulse.dur = stop_time - start_time
        currents.play(pulse._ref_amp, time)


    def get_childrensections(self, parentsection):
        """Get the children section of a neuron section"""
        number_children = neuron.h.SectionRef(sec=parentsection).nchild()
        children = []
        for index in range(0, int(number_children)):
            children.append(neuron.h.SectionRef(sec=self.soma).child[index])
        return children


    def get_parentsection(self, childsection):
        """Get the parent section of a neuron section"""
        print self.soma
        return neuron.h.SectionRef(sec=childsection).parent


    def addAxialCurrentRecordings(self, section):
        """Create a recording that will contain all the axial current flowing in and out of the section"""
        secname = neuron.h.secname(sec=section)
        self.addRecording(secname)
        for child in self.get_childrensections(section):
            self.addRecording(child)
        self.get_parentsection(section)


    def getAxialCurrentRecording(self, section):
        """Return the axial current recording"""
        secname = neuron.h.secname(sec=section)
        for child in self.get_childrensections(section):
            self.getRecording(secname)
            self.getRecording(child)


    def somatic_branches(self):
        """Show the index numbers """
        nchild = neuron.h.SectionRef(sec=self.soma).nchild()
        for index in range(0, int(nchild)):
            secname = neuron.h.secname(sec=neuron.h.SectionRef(sec=self.soma).child[index])
            if not "axon" in secname:
                if "dend" in secname:
                    dendnumber = int(secname.split("dend")[1].split("[")[1].split("]")[0])
                    secnumber = int(self.cell.getCell().nSecAxonalOrig + self.cell.getCell().nSecSoma + dendnumber)
                    print dendnumber, secnumber
                elif "apic" in secname:
                    apicnumber = int(secname.split("apic")[1].split("[")[1].split("]")[0])
                    secnumber = int(self.cell.getCell().nSecAxonalOrig + self.cell.getCell().nSecSoma + self.cell.getCell().nSecBasal + apicnumber)
                    print apicnumber, secnumber
                else:
                    raise Exception("somaticbranches: No apic or dend found in section %s" % secname)


    def apical_trunk(self):
        """Return the apical trunk of the cell"""
        if len(self.apical) is 0:
            return []
        else:
            apicaltrunk = []
            apicaltrunk.append(self.apical[0])
            currentsection = self.apical[0]
            while True:
                children = [neuron.h.SectionRef(sec=currentsection).child[index] for index in range(0, int(neuron.h.SectionRef(sec=currentsection).nchild()))]
                if len(children) is 0:
                    break
                maxdiam = 0
                for child in children:
                    if child.diam > maxdiam:
                        currentsection = child
                        maxdiam = child.diam
                apicaltrunk.append(child)
            return apicaltrunk


    def addRamp(self, start_time, stop_time, start_level, stop_level, dt=0.1):
        """Add a ramp current injection"""
        t_content = numpy.arange(start_time, stop_time, dt)
        i_content = [((stop_level-start_level)/(stop_time-start_time))*(x-start_time)+start_level for x in t_content]
        self.injectCurrentWaveform(t_content, i_content)


    def addVClamp(self, stop_time, level):
        """Add a voltage clamp"""
        vclamp = neuron.h.SEClamp(0.5, sec=self.soma)
        vclamp.amp1 = level
        vclamp.dur1 = stop_time
        vclamp.dur2 = 0
        vclamp.dur3 = 0
        self.persistent.objects.append(vclamp)


    def addSineCurrentInject(self, start_time, stop_time, freq, amplitude, mid_level, dt=1.0):
        """Add a sinusoidal current injection"""
        t_content = numpy.arange(start_time, stop_time, dt)
        i_content = [amplitude*math.sin(freq*(x-start_time)*(2*math.pi))+mid_level for x in t_content]
        self.injectCurrentWaveform(t_content, i_content)
        return (t_content, i_content)


    def getTime(self):
        """Get the time vector"""
        return numpy.array(self.getRecording('neuron.h._ref_t'))


    def getSomaVoltage(self):
        """Get a vector of the soma voltage"""
        return numpy.array(self.getRecording('soma(0.5)._ref_v'))


    def getNumberOfSegments(self):
        """Get the number of segments in the cell"""
        totalnseg = 0
        for section in self.all:
            totalnseg += section.nseg
        return totalnseg


    def addPlotWindow(self, var_list, xlim=None, ylim=None, title=""):
        """Add a window to plot a variable"""
        xlim = [0, 1000] if xlim is None else xlim
        ylim = [-100, 100] if ylim is None else ylim
        for var_name in var_list:
            if var_name not in self.recordings:
                self.addRecording(var_name)
        self.plotWindows.append(PlotWindow(var_list, self, xlim, ylim, title))


    def showDendrogram(self, variable=None, active=False):
        """Show a dendrogram of the cell"""
        cell_dendrogram = dendrogram([x for x in self.cell.getCell().all], variable=variable, active=active)
        cell_dendrogram.redraw()
        self.cell_dendrograms.append(cell_dendrogram)


    def update(self):
        """Update all the windows"""
        for window in self.plotWindows:
            window.redraw()
        for cell_dendrogram in self.cell_dendrograms:
            cell_dendrogram.redraw()


    def delete(self):
        """Delete the cell"""
        if self.cell:
            if self.cell.getCell():
                self.cell.getCell().clear()
        #for window in self.plotWindows:
        #    window.process.join()
        ''' BTN, clear mechanisms as well '''
        self.mechanisms = []
        del(self.mechanisms)

    def __del__(self):
        self.delete()

def calculate_inputresistance(template_name, morphology_name, current_delta=0.01):
    """Calculate the input resistance at rest of the cell"""
    rest_voltage = calculate_SS_voltage(template_name, morphology_name, 0.0)
    step_voltage = calculate_SS_voltage(template_name, morphology_name, current_delta)

    voltage_delta = step_voltage - rest_voltage

    return voltage_delta/current_delta

def calculate_SS_voltage(template_name, morphology_name, step_level):
    """Calculate the steady state voltage at a certain current step"""
    pool = multiprocessing.Pool(processes=1)
    SS_voltage = pool.apply(calculate_SS_voltage_subprocess, [template_name, morphology_name, step_level])
    pool.terminate()
    return SS_voltage

def calculate_SS_voltage_subprocess(template_name, morphology_name, step_level):
    """Subprocess wrapper of calculate_SS_voltage"""
    cell = Cell(template_name, morphology_name)
    cell.addRamp(500, 5000, step_level, step_level, dt=1.0)
    simulation = Simulation()
    simulation.run(1000)
    time = cell.getTime()
    voltage = cell.getSomaVoltage()
    SS_voltage = numpy.mean(voltage[numpy.where((time < 1000) & (time > 800))])
    cell.delete()

    return SS_voltage


def search_hyp_current(template_name, morphology_name, hyp_voltage, start_current, stop_current):
    """Search current necessary to bring cell to -85 mV"""
    med_current = start_current + abs(start_current-stop_current)/2
    new_hyp_voltage = calculate_SS_voltage(template_name, morphology_name, med_current)
    print "Detected voltage: ", new_hyp_voltage
    if abs(new_hyp_voltage - hyp_voltage) < .5:
        return med_current
    elif new_hyp_voltage > hyp_voltage:
        return search_hyp_current(template_name, morphology_name, hyp_voltage, start_current, med_current)
    elif new_hyp_voltage < hyp_voltage:
        return search_hyp_current(template_name, morphology_name, hyp_voltage, med_current, stop_current)


def detect_hyp_current(template_name, morphology_name, hyp_voltage):
    """Search current necessary to bring cell to -85 mV"""
    return search_hyp_current(template_name, morphology_name, hyp_voltage, -1.0, 0.0)


def detect_spike_step(template_name, morphology_name, hyp_level, inj_start, inj_stop, step_level):
    """Detect if there is a spike at a certain step level"""
    pool = multiprocessing.Pool(processes=1)
    spike_detected = pool.apply(detect_spike_step_subprocess, [template_name, morphology_name, hyp_level, inj_start, inj_stop, step_level])
    pool.terminate()
    return spike_detected


def detect_spike_step_subprocess(template_name, morphology_name, hyp_level, inj_start, inj_stop, step_level):
    """Detect if there is a spike at a certain step level"""
    cell = Cell(template_name, morphology_name)
    cell.addRamp(0, 5000, hyp_level, hyp_level, dt=1.0)
    cell.addRamp(inj_start, inj_stop, step_level, step_level, dt=1.0)
    simulation = Simulation()
    simulation.run(int(inj_stop))

    time = cell.getTime()
    voltage = cell.getSomaVoltage()
    time_step = time[numpy.where((time > inj_start) & (time < inj_stop))]
    voltage_step = voltage[numpy.where((time_step > inj_start) & (time_step < inj_stop))]
    spike_detected = numpy.max(voltage_step) > -20

    cell.delete()

    return spike_detected

def search_threshold_current(template_name, morphology_name, hyp_level, inj_start, inj_stop, start_current, stop_current):
    """Search current necessary to reach threshold"""
    med_current = start_current + abs(start_current-stop_current)/2
    spike_detected = detect_spike_step(template_name, morphology_name, hyp_level, inj_start, inj_stop, med_current)
    print "Spike threshold detection at: ", med_current, "nA", spike_detected

    if abs(stop_current - start_current) < .01:
        return stop_current
    elif spike_detected:
        return search_threshold_current(template_name, morphology_name, hyp_level, inj_start, inj_stop, start_current, med_current)
    elif not spike_detected:
        return search_threshold_current(template_name, morphology_name, hyp_level, inj_start, inj_stop, med_current, stop_current)

def detect_threshold_current(template_name, morphology_name, hyp_level, inj_start, inj_stop):
    """Search current necessary to reach threshold"""
    return search_threshold_current(template_name, morphology_name, hyp_level, inj_start, inj_stop, 0.0, 1.0)

'''
def calculateAllSynapticAttenuations(bglibcell):
    sim = Simulation()
    sim.addCell(bglibcell)

    bglibcell.addAllSectionsVoltageRecordings()

    basal_sections = [x for x in bglibcell.cell.getCell().basal]
    apical_sections = [x for x in bglibcell.cell.getCell().apical]
    #dendritic_sections = basal_sections + apical_sections
    thick_apical_sections = [section for section in apical_sections if section.diam > .6]
    thin_apical_sections = [section for section in apical_sections if section.diam < .7]
    random.shuffle(thin_apical_sections, random.random)
    normdistances = []
    absdistances = []
    attenuations = []
    sectiontypes = []

    [secnumber, location] = bglibcell.locateBAPSite("apic", 200)
    #print secnumber, location
    #for record_section in [apical_sections[int(secnumber)], apical_sections[int(secnumber)], apical_sections[int(secnumber)], apical_sections[int(secnumber)], apical_sections[int(secnumber)]]:
    for record_section in bglibcell.apicaltrunk(): #thick_apical_sections:
        location = 0.5
        print record_section.name()
        source_section = thin_apical_sections.pop()
        #source_segname = source_section.name() + "(" + str(location) + ")"
        synapse = neuron.h.tmgExSyn(location, sec=source_section)
        #synapse.Use = 0.02
        # synapse.Use = 0.5
        #synapse.Dep = 194
        # synapse.Dep = 671
        #synapse.Fac = 507
        # synapse.Fac = 17
        #if section in apical_sections and section.diam > .575:
        # synapse.gmax = .0000002
        #else:
        #    synapse.gmax = .00000005
        netstim = neuron.h.NetStim(sec=source_section)
        stimfreq = 70
        netstim.interval = 1000/stimfreq
        netstim.number = 1
        netstim.start = 300
        netstim.noise = 0
        connection = neuron.h.NetCon(netstim, synapse, 10, 0, 700, sec=source_section)
        connection.weight[0] = 1.0
        sim.run(600)
        time = bglibcell.getTime()
        allsectionrecordings = bglibcell.getAllSectionsVoltageRecordings()
        soma = [x for x in bglibcell.cell.getCell().somatic][0]
        somavoltage = numpy.array(allsectionrecordings[soma.name()])
        dendvoltage = numpy.array(allsectionrecordings[record_section.name()])
        #pylab.plot(time, somavoltage, label="soma")
        #pylab.plot(time, dendvoltage, label="dend")
        #pylab.legend()
        #pylab.show()
        del connection

        interval_indices = numpy.where((time > netstim.start) & (time < netstim.start+90))
        max_soma = max(somavoltage[numpy.where((time > netstim.start) & (time < netstim.start+90))])
        min_soma = numpy.min(somavoltage[interval_indices])
        amp_soma = max_soma - min_soma
        max_dend = numpy.max(dendvoltage[interval_indices])
        min_dend = numpy.min(dendvoltage[interval_indices])
        amp_dend = max_dend - min_dend
        attenuation = amp_dend / amp_soma
        attenuations.append(attenuation)
        neuron.h.distance(sec=soma)
        absdistance = neuron.h.distance(location, sec=record_section)
        absdistances.append(absdistance)
        if record_section in basal_sections:
            sectiontypes.append("basal")
            normdistance = absdistance/bglibcell.cell.getCell().getLongestBranch("basal")
        elif record_section in apical_sections:
            sectiontypes.append("apical")
            normdistance = absdistance/bglibcell.cell.getCell().getLongestBranch("apic")
        else:
            sectiontypes.append("apical")
            normdistance = absdistance/bglibcell.cell.getCell().getLongestBranch("apic")
            print "Section is not in apical nor basal"
            #exit(1)
        normdistances.append(normdistance)


    return normdistances, absdistances, attenuations, sectiontypes

def calculateAllSSAttenuations(bglibcell):
    sim = Simulation()
    sim.addCell(bglibcell)

    bglibcell.addAllSectionsVoltageRecordings()

    basal_sections = [x for x in bglibcell.cell.getCell().basal]
    apical_sections = [x for x in bglibcell.cell.getCell().apical]
    dendritic_sections = basal_sections + apical_sections
    normdistances = []
    absdistances = []
    attenuations = []
    sectiontypes = []

    for section in dendritic_sections:
        for location in [0.5]:
            segname = section.name() + "(" + str(location) + ")"
            print segname
            clamp = neuron.h.IClamp(0.5, sec=section)
            clamp.dur = 300
            clamp.delay = 150
            clamp.amp = 0.01
            sim.run(300)

            time = bglibcell.getTime()
            allsectionrecordings = bglibcell.getAllSectionsVoltageRecordings()
            soma = [x for x in bglibcell.cell.getCell().somatic][0]
            somavoltage = numpy.array(allsectionrecordings[soma.name()])
            dendvoltage = numpy.array(allsectionrecordings[section.name()])

            interval_indices = numpy.where((time > clamp.delay) & (time < clamp.delay+90))
            max_soma = max(somavoltage[numpy.where((time > clamp.delay) & (time < clamp.delay+90))])
            min_soma = numpy.min(somavoltage[interval_indices])
            amp_soma = max_soma - min_soma
            max_dend = numpy.max(dendvoltage[interval_indices])
            min_dend = numpy.min(dendvoltage[interval_indices])
            amp_dend = max_dend - min_dend
            attenuation = amp_dend / amp_soma
            attenuations.append(attenuation)
            neuron.h.distance(sec=soma)
            absdistance = neuron.h.distance(location, sec=section)
            absdistances.append(absdistance)
            if section in basal_sections:
                sectiontypes.append("basal")
                normdistance = absdistance/bglibcell.cell.getCell().getLongestBranch("basal")
            elif section in apical_sections:
                sectiontypes.append("apical")
                normdistance = absdistance/bglibcell.cell.getCell().getLongestBranch("apic")
            else:
                print "Section is not in apical nor basal"
                exit(1)
            normdistances.append(normdistance)


    return normdistances, absdistances, attenuations, sectiontypes
'''

class PlotWindow:
    """Class the represents a plotting window"""

    def __init__(self, var_list, cell, xlim, ylim, title):
        self.cell = cell
        self.var_list = var_list
        pylab.ion()
        self.figure = pylab.figure(figsize=(10, 10))
        pylab.ioff()

        self.ax = self.figure.gca()
        self.canvas = self.ax.figure.canvas

        self.figure.suptitle(title)
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.ax.set_xlabel("ms")
        self.ax.set_ylabel("mV")

        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.line = {}

        linenumber = 0
        for var_name in self.var_list:
            recording = self.cell.getRecording(var_name)
            if recording:
                time = self.cell.getTime()
            else:
                time = self.cell.getTime()[1:]

            #print dir(pylab.gca()._get_lines)
            #print pylab.gca()._get_lines.color_cycle
            linecolors = [x for x in itertools.islice(pylab.gca()._get_lines.color_cycle, 0, 50)]
            self.line[var_name] = pylab.Line2D(time, recording, label=var_name, color=linecolors[linenumber % len(linecolors)])
            self.ax.add_line(self.line[var_name])
            linenumber += 1

        self.ax.legend()

        self.figure.canvas.draw()

        self.drawCount = 10

    def redraw(self):
        """Redraw the plot window"""
        if not self.drawCount:
            time = self.cell.getTime()
            for var_name in self.var_list:
                voltage = self.cell.getRecording(var_name)
                self.line[var_name].set_data(time, voltage)
                self.ax.draw_artist(self.line[var_name])
            self.canvas.blit(self.ax.bbox)
            self.drawCount = 100
        else:
            self.drawCount = self.drawCount - 1
        return True


class dendrogram:
    """Class that represent a dendrogram plot"""
    def __init__(self, sections, variable=None, active=False):
        pylab.ion()
        self.dend_figure = pylab.figure(figsize=(20, 12))
        pylab.ioff()


        self.sections = sections
        neuron.h.finitialize()

        self.hroot = neuron.h.SectionRef(sec=self.sections[0]).root
        self.proot = PSection(self.hroot, None)
        self.psections = [self.proot] + self.proot.getAllPDescendants()

        pylab.xlim([0, self.proot.treeWidth()+self.proot.ySpacing])
        pylab.ylim([0, self.proot.treeHeight()+self.proot.xSpacing])
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
        cbar.ax.set_yticklabels(["%.2e"%(varbounds[0]), "%.2e"%(varbounds[1])])

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


class PSection:
    """Class that represents a cell section"""
    def __init__(self, hsection, pparent):
        self.L = hsection.L
        self.diam = hsection.diam
        self.hsection = hsection
        self.name = neuron.h.secname(sec=hsection)
        self.pparent = pparent
        self.hchildren = [neuron.h.SectionRef(sec=self.hsection).child[index] for index in range(0, int(neuron.h.SectionRef(sec=self.hsection).nchild()))]
        self.pchildren = []
        for hchild in self.hchildren:
            self.pchildren.append(PSection(hchild, self))
        self.isLeaf = False
        if not self.hchildren:
            self.isLeaf = True

        self.psegments = []
        self.maxsegdiam = 0
        for hsegment in hsection:
            psegment = PSegment(hsection(hsegment.x), self)
            self.psegments.append(psegment)
            self.maxsegdiam = max(self.maxsegdiam, psegment.diam)

        self.xSpacing = 10
        self.ySpacing = 1

    def setupDraw(self, figure, x, y, variable=None, varbounds=None):
        """Setup draw of psection"""
        y_accum = 0
        for psegment in self.psegments:
            psegment.setupDraw(figure, x + (self.maxsegdiam-psegment.diam)/2, y + y_accum, variable=variable, varbounds=varbounds)
            y_accum += psegment.L

    def redraw(self):
        """Redraw psection"""
        for psegment in self.psegments:
            psegment.redraw()

    def getSectionVarBounds(self, variable):
        """Get bounds a variable in a section"""
        varmin = None
        varmax = None
        for psegment in self.psegments:
            value = psegment.getVariableValue(variable)
            if value:
                varmin = min(value, varmin) if varmin else value
                varmax = max(value, varmax) if varmax else value
        return [varmin, varmax]

    def getTreeVarBounds(self, variable):
        """Get the bounds of a variable in a dendritic subtree"""
        varbounds = self.getSectionVarBounds(variable)
        for child in self.pchildren:
            child_varbounds = child.getTreeVarBounds(variable)
            if child_varbounds[0] and child_varbounds[1]:
                varbounds[0] = min(varbounds[0], child_varbounds[0]) if varbounds[0] else child_varbounds[0]
                varbounds[1] = max(varbounds[1], child_varbounds[1]) if varbounds[1] else child_varbounds[1]

        return varbounds

    def drawTree(self, figure, x, y, variable=None, varbounds=None):
        """Draw a dendritic tree"""
        self.setupDraw(figure, x, y, variable=variable, varbounds=varbounds)
        new_x = x # + self.L + self.xSpacing
        new_y = y + self.L + self.xSpacing
        for child in self.pchildren:
            child.drawTree(figure, new_x, new_y, variable=variable, varbounds=varbounds)
            pylab.plot([x+self.diam/2, new_x+child.diam/2], [y+self.L, new_y], 'k')
            new_x = new_x + child.treeWidth()

    def treeWidth(self):
        """Width of a dendritic tree"""
        if self.isLeaf:
            treeWidth = self.maxsegdiam + self.ySpacing
        else:
            treeWidth = 0
            for child in self.pchildren:
                treeWidth += child.treeWidth()

        return max(self.diam + self.ySpacing, treeWidth)

    def treeHeight(self):
        """Height of dendritic tree"""
        return self.L + self.xSpacing + (max([child.treeHeight() for child in self.pchildren]) if self.pchildren else 0)

    def getHChildren(self):
        """All hoc children of a section"""
        return self.hchildren

    def getPParent(self):
        """The python parent of a section"""
        return self.parent

    def getHParent(self):
        """The hoc parent of a section"""
        return self.parent.hsection

    def getAllPDescendants(self):
        """The python descendents of a section"""
        pdescendants = [x for x in self.pchildren]
        for child in self.pchildren:
            pdescendants += child.getAllPDescendants()
        return pdescendants

    def getAllPLeaves(self):
        """All the python leaves of a tree"""
        pleaves = []
        if not self.pchildren:
            pleaves.append(self)
        else:
            for child in self.pchildren:
                pleaves += child.getAllPLeaves()
        return pleaves

class PSegment:
    """A python representation of a segment"""
    def __init__(self, hsegment, parentsection):
        self.hsegment = hsegment
        self.parentsection = parentsection
        self.L = self.parentsection.L/self.parentsection.hsection.nseg
        self.diam = self.hsegment.diam

        self.figure = None
        self.figX = None
        self.figY = None
        self.color_map = plt.cm.get_cmap("hot")
        self.ax = None
        self.patch = None
        self.plotvariable = None
        self.mechanism_names = [mechanism.name() for mechanism in hsegment]
        self.varbounds = None

    def setupDraw(self, figure, x, y, variable=None, varbounds=None):
        """Set up the drawing of a segment"""
        self.figure = figure
        self.plotvariable = variable
        self.varbounds = varbounds
        self.ax = self.figure.gca()
        self.figX = x
        self.figY = y
        self.patch = plt.patches.Rectangle([self.figX, self.figY], self.diam, self.L, facecolor="white", edgecolor="black")
        self.ax.add_patch(self.patch)

    def redraw(self):
        """Redraw a segment"""
        if self.plotvariable:
            plotvariable_value = self.getVariableValue(self.plotvariable)
            if not plotvariable_value is None:
                self.patch.set_facecolor(self.color_map((plotvariable_value-self.varbounds[0])/(self.varbounds[1]-self.varbounds[0])))
            else:
                self.patch.set_facecolor(self.color_map(1.0))
                self.patch.set_hatch("/")
            self.ax.draw_artist(self.patch)


    def getVariableValue(self, variable):
        """Get a variable value in a segment"""
        if variable is "v" or neuron.h.execute1("{%s.%s(%f)}" % (neuron.h.secname(sec=self.parentsection.hsection), variable, self.hsegment.x), 0):
            return eval("self.hsegment."+variable)
        else:
            return None

class Simulation:
    """Class that represents a neuron simulation"""
    def __init__(self, verbose_level=0):
        self.verbose_level = verbose_level
        self.cells = []
        neuron.h.celsius = 34
        #self.steps_per_ms = 1

    def addCell(self, new_cell):
        """Add a cell to a simulation"""
        self.cells.append(new_cell)

    def run(self, maxtime, cvode=True, v_init=-65, dt=0.025):
        """Run the simulation"""
        neuron.h.tstop = 0.000001
        #print "dt=", neuron.h.dt
        neuron.h.dt = dt
        neuron.h.v_init = v_init

        if cvode:
            neuron.h('{cvode_active(1)}')
        else:
            neuron.h('{cvode_active(0)}')

        neuron.h.finitialize()

        try:
            neuron.h.run()
        except Exception, e:
            print 'The Interneuron was eaten by the Python !\nReason: %s: %s' % (e.__class__.__name__, e)

        self.continuerun(maxtime)

    def continuerun(self, maxtime):
        """Continue a running simulation"""
        while neuron.h.t < maxtime:
            for cell in self.cells:
                cell.update()
            if self.verbose_level >= 1:
                print str(neuron.h.t) + " ms"
            try:
                neuron.h.step()
            except Exception, e:
                print 'The Interneuron was eaten by the Python !\nReason: %s: %s' % (e.__class__.__name__, e)
                break

    def __del__(self):
        pass