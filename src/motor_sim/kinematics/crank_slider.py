import math

class CrankSliderKinematics:
    def __init__(self, bore_m, stroke_m, conrod_m, compression_ratio):
        self.bore = float(bore_m)
        self.stroke = float(stroke_m)
        self.r = 0.5 * self.stroke
        self.l = float(conrod_m)
        self.A = math.pi * (0.5 * self.bore) ** 2
        self.Vs = self.A * self.stroke
        cr = float(compression_ratio)
        self.Vc = self.Vs / (cr - 1.0)

    def x_from_tdc(self, theta):
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        under = max(self.l**2 - (self.r*sin_t)**2, 0.0)
        return self.r*(1.0 - cos_t) + (self.l - math.sqrt(under))

    def dx_dtheta(self, theta):
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        denom_sq = self.l**2 - (self.r*sin_t)**2
        denom = math.sqrt(max(denom_sq, 1e-30))
        return self.r*sin_t + (self.r**2 * sin_t * cos_t) / denom

    def volume_dVdtheta_x(self, theta):
        x = self.x_from_tdc(theta)
        dx = self.dx_dtheta(theta)
        V = self.Vc + self.A * x
        dV_dtheta = self.A * dx
        return V, dV_dtheta, x
