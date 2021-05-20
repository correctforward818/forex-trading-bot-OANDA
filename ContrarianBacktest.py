import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tpqoa

plt.style.use("seaborn")


class ContrarianBacktest:
    """
    Class implementing vectorized back-testing of a Contrarian Strategy.
    This strategy should only be used alongside other strategies, on it's own it is very sensitive
    to the value of the moving window set for the strategy.
    Also note, these strategies change positions many times, which can lead to trading costs diminishing your
    profits, or magnifying your losses.
    """
    def __init__(self, symbol, start, end, window=1, granularity="D", trading_cost=0):

        self._symbol = symbol
        self._start = start
        self._end = end
        self._window = window
        self._granularity = granularity
        self._tc = trading_cost

        self._results = None

        self._data = self.acquire_data()

    def __repr__(self):
        return f"ContrarianBacktest( symbol={self._symbol}, start={self._start}, end={self._end}, granularity={self._granularity}, window={self._window}, trading_cost={self._tc} )";

    def acquire_data(self):
        """
        A general function to acquire data of symbol from a source.

        Returns:
            Returns a Pandas dataframe containing downloaded info.
        """

        oanda = tpqoa.tpqoa('oanda.cfg')

        try:
            df = oanda.get_history(self._symbol, self._start, self._end, self._granularity, "B")
        except:
            raise ValueError("Please choose a supported instrument trading on OANDA, in the form XXX/YYY or XXX_YYY.")


        # only care for the closing price
        df = df.c.to_frame()
        df.rename(columns={"c": "price"}, inplace=True)

        df.dropna(inplace=True)

        df["returns"] = np.log(df.div(df.shift(1)))

        return df

    def resample(self, granularity):
        """
        Resamples the symbols dataset to be in buckets of the passed granularity (IE "W", "D", "H").

        Args:
            granularity (string): The new granularity for the dataset
        """
        self._granularity = granularity
        self._data.resample(granularity)
        return

    def get_data(self):
        """
        Getter function to retrieve current symbol's dataframe.

        Returns:
            Returns the stored Pandas dataframe with information regarding the symbol
        """
        return self._data

    def get_results(self):
        """
        Getter function to retrieve current instrument's dataframe after testing the strategy.

        Returns:
            Returns a Pandas dataframe with results from back-testing the strategy
        """
        if self._results is not None:
            return self._results
        else:
            print("Please run .test() first.")

    def test(self, window=1):
        """
        Executes the back-testing of the Contrarian strategy on the set instrument.

        Returns:
            Returns a tuple, (float: performance, float: out_performance)
            -> "performance" is the percentage of return on the interval [start, end]
            -> "out_performance" is the performance when compared to a buy & hold on the same interval
                IE, if out_performance is greater than one, the strategy outperformed B&H.
        """
        # IE if no window parameter included and we have a stored window, use that as the window instead
        if self._window != 1 and window == 1:
            window = self._window

        data = self._data.copy()

        data["position"] = -np.sign(data["returns"].rolling(window).mean())
        data["strategy"] = data["position"].shift(1) * data["returns"]

        data.dropna(inplace=True)

        # running total of amount of trades currently, each change of position is 2 trades, but can be improved.
        # TODO: likely can save one trade by combining closing of position and opening of opposite position into one trade
        # (ie current open position LONG 100 shares -> open postion SHORT (current open position shares + additional
        # shares)
        data["trades"] = data.position.diff().fillna(0).abs()

        # correct strategy returns based on trading costs
        data.strategy = data.strategy - data.trades * self._tc

        data["creturns"] = data["returns"].cumsum().apply(np.exp)
        data["cstrategy"] = data["strategy"].cumsum().apply(np.exp)

        self._results = data

        performance = data["cstrategy"].iloc[-1]
        # out_performance is our strats performance vs a buy and hold on the interval
        out_performance = performance - data["creturns"].iloc[-1]

        return performance, out_performance

    def optimize(self, window_range=(1,252)):
        """
        Optimizes the window on the interval [start,end] which allows for the greatest return.

        Args:
            window_range (tuple(int, int)) <DEFAULT>=(1,252): Range of values for optimization of sliding window

        Returns:
            Returns a tuple, (float: max_return, int: best_window)
            -> "max_return" is the optimized (maximum) return rate of the instrument on the interval [start,end]
            -> "best_window" is the optimized window that enables a maximum return
        """

        if window_range[0] >= window_range[1]:
            print("The range must satisfy: (X,Y) -> X < Y")
            return

        max_return = float('-inf')
        best_window = 1

        for window in range(window_range[0], window_range[1]):

            if window == (window_range[1]/4): print("25%...")
            if window == (window_range[1]/2): print("50%...")
            if window == (window_range[1]/1.5): print("75%...")

            current_return = self.test(window)[0]

            if current_return > max_return:
                max_return = current_return
                best_window = window

        # save the optimized window
        self._window = best_window

        # run the final test to store results
        self.test()

        return max_return, best_window

    def plot_results(self):
        """
        Plots the results of test() or optimize().
        Also plots the results of the buy and hold strategy on the interval [start,end] to compare to the results.
        """
        if self._results is not None:
            title = f"{self._symbol} | window {self._window}"
            self._results[["creturns", "cstrategy"]].plot(title=title, figsize=(12, 8))
            plt.show()
        else:
            print("Please run test() or optimize().")