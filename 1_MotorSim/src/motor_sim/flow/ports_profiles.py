import numpy as np
from dataclasses import dataclass
from .table_io import load_3col

@dataclass
class PortsArea:
    theta_deg: np.ndarray
    A_in: np.ndarray
    A_ex: np.ndarray

    @staticmethod
    def from_file(area_file: str) -> "PortsArea":
        th, Ain, Aex = load_3col(area_file)
        return PortsArea(theta_deg=th, A_in=Ain, A_ex=Aex)

    def area(self, theta_deg: float):
        Ain = float(np.interp(theta_deg, self.theta_deg, self.A_in))
        Aex = float(np.interp(theta_deg, self.theta_deg, self.A_ex))
        return Ain, Aex

@dataclass
class AlphaK:
    theta_deg: np.ndarray
    ak_in: np.ndarray
    ak_ex: np.ndarray

    @staticmethod
    def from_file(alphak_file: str) -> "AlphaK":
        th, aKi, aKe = load_3col(alphak_file)
        return AlphaK(theta_deg=th, ak_in=aKi, ak_ex=aKe)

    def eval(self, theta_deg: float):
        aKi = float(np.interp(theta_deg, self.theta_deg, self.ak_in))
        aKe = float(np.interp(theta_deg, self.theta_deg, self.ak_ex))
        return aKi, aKe
