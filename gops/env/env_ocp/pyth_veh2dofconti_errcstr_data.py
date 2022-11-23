#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: iDLab
#  Description: Vehicle 2DOF data environment with tracking error constraint

import numpy as np

from gops.env.env_ocp.pyth_veh2dofconti_data import SimuVeh2dofconti


class SimuVeh2dofcontiErrCstr(SimuVeh2dofconti):
    def __init__(
        self,
        path_para:dict = None, 
        u_para:dict = None, 
        y_error_tol: float = 0.2, 
        **kwargs,
    ):
        super().__init__(path_para, u_para, **kwargs)
        self.y_error_tol = y_error_tol
        self.info_dict.update({
            "constraint": {"shape": (1,), "dtype": np.float32},
        })

    def get_constraint(self) -> np.ndarray:
        y = self.state[0]
        y_ref = self.ref_traj.compute_y(self.t, self.path_num, self.u_num)
        constraint = np.array([abs(y - y_ref) - self.y_error_tol], dtype=np.float32)
        return constraint

    @property
    def info(self):
        info = super().info
        info.update({
            "constraint": self.get_constraint(),
        })
        return info


def env_creator(**kwargs):
    return SimuVeh2dofcontiErrCstr(**kwargs)