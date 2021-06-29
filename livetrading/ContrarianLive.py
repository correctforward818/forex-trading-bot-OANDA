import numpy as np

from livetrading.LiveTrader import LiveTrader


class ContrarianLive(LiveTrader):
    def __init__(
        self,
        cfg,
        instrument,
        bar_length,
        window,
        units,
        stop_datetime=None,
        stop_loss=None,
        stop_profit=None,
    ):

        self._window = window

        # passes params to the parent class
        super().__init__(
            cfg,
            instrument,
            bar_length,
            units,
            stop_datetime=stop_datetime,
            stop_loss=stop_loss,
            stop_profit=stop_profit,
        )

    def define_strategy(self):
        data = self._raw_data.copy()
        data["returns"] = np.log(data["mid_price"].div(data["mid_price"].shift(1)))
        data["position"] = -np.sign(data["returns"].rolling(self._window).mean())
        self._data = data.dropna().copy()