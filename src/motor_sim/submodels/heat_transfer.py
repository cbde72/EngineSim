# Placeholder for v2 extension: implement Woschni/Annand etc.
class HeatTransfer:
    def contribute(self, t, y, ctx, aux, dy):
        # Example hook:
        # Qdot_w = h*A*(aux["T"] - Tw)
        # dy[ctx.model_state.i("T")] += -Qdot_w/(ctx.gas.cv*max(aux["m"],1e-9))
        pass
