class AdaptiveRTO:
    def __init__(self, initial_rto=0.2, alpha=0.125, beta=0.25, min_rto=0.05, max_rto=1.0):
        self.srtt = None
        self.rttvar = None
        self.rto = initial_rto
        self.alpha = alpha
        self.beta = beta
        self.min_rto = min_rto
        self.max_rto = max_rto

    def update(self, measured_rtt: float, is_retransmission: bool):
        if is_retransmission:
            self.rto = min(self.rto * 1.5, self.max_rto)
            return self.rto

        if self.srtt is None:
            self.srtt = measured_rtt
            self.rttvar = measured_rtt / 2.0
        else:
            self.rttvar = (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - measured_rtt)
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * measured_rtt

        self.rto = self.srtt + max(0.02, 4.0 * self.rttvar)
        self.rto = max(self.min_rto, min(self.rto, self.max_rto))
        return self.rto