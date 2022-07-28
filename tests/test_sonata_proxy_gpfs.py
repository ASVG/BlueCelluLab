"""Tests the sonata proxy using a sim on gpfs."""

from pytest import approx

from bglibpy.cell import SonataProxy
from bglibpy.circuit import CircuitAccess


test_relative_ornstein_path = (
    "/gpfs/bbp.cscs.ch/data/scratch/proj96/home/ecker/simulations/"
    "LayerWiseEOUNoise_Ca1p15/BlueConfig")


class TestSonataProxy:

    def setup(self):
        circuit_access = CircuitAccess(test_relative_ornstein_path)
        gid = 1
        self.sonata_proxy = SonataProxy(gid, circuit_access)

    def test_get_input_resistance(self):
        assert self.sonata_proxy.get_input_resistance().iloc[0] == approx(262.087372)
