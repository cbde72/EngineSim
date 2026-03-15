Valve lift input file supports angles in crank-deg or cam-deg.
Set in config.json:
  gasexchange.valves.lift_angle_basis = 'crank' or 'cam'
  gasexchange.valves.cam_to_crank_ratio = 2.0 (4T default)

Timing alignment:
  intake_open.align / exhaust_open.align = 'open' or 'close'
The provided classic timing dict is interpreted as the target angle of that event.

Effective opening phase threshold:
  gasexchange.valves.effective_lift_threshold_mm (default 0.1)
Angle scaling is performed about the CENTER of the effective phase (lift > threshold).
