#!/usr/bin/env bash
module load $HOME/rhel6-mvapich2-psm-x86_64-shared-dev.synapseid
#mpirun -n 2 -genvall $BGLIB_ROOT/bin/special $BGLIB_HOCLIB/PrepConfig.hoc -c 'configFile="BlueConfig"' $BGLIB_HOCLIB/init.hoc -mpi -NFRAME 256
#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/nfs4/bbp.epfl.ch/sw/bbp-stack/reportinglib/dev-git/install/lib
#mpirun -n 2 -genvall /home/vangeit/src/BlueBrain/lib/x86_64/special  $BGLIB_HOCLIB/PrepConfig.hoc -c "configFile=\"BlueConfig\"" $BGLIB_HOCLIB/init.hoc -mpi -NFRAME 256
#export BGLIB_HOCLIB="$HOME/src/BlueBrain/lib/hoclib"
#mpirun -n 2 -genvall /nfs4/bbp.epfl.ch/sw/bbp-stack/bglib/1.6.0-dev/install-shared/bin/special  $BGLIB_HOCLIB/PrepConfig.hoc -c "configFile=\"BlueConfig\"" $BGLIB_HOCLIB/init.hoc -mpi -NFRAME 256
mpirun -n 2 -genvall /home/vangeit/src/BlueBrain/lib/x86_64/special   $BGLIB_HOCLIB/PrepConfig.hoc -c "configFile=\"BlueConfig\"" $BGLIB_HOCLIB/init.hoc -mpi -NFRAME 256
cd output
#python /home/vangeit/local/pybinreports/bin/soma2h5.py
cp out.dat.original out.dat