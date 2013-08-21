# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import division

import datetime
from math import sqrt, log, pi, cos, sin, exp

from configman import Namespace
from socorro.cron.base import PostgresBackfillCronApp


def mean(x):
    """Computes the mean of the list of values x.

    Args:
        x: the list of values.
    """
    return sum(x) / len(x)


def var(x, ddof=0):
    """Computes the variance of the list of values x

    Args:
        x: The list of values
        ddof: Means Delta Degrees of Freedom. Used for the N - ddof
    """
    N = len(x)
    m = mean(x)
    s = 0
    for v in x:
        s += (v - m) ** 2

    return s / (N - ddof)


def std(x, ddof=0):
    """Computes the standard deviation of a list of values x

    Args:
        x: The list of values
        ddof: Means Delta Degrees of Freedom
    """
    return sqrt(var(x, ddof))

# magic constants for inv norm cdf.
# see http://home.online.no/~pjacklam/notes/invnorm/
a1 = -3.969683028665376e+01
a2 = 2.209460984245205e+02
a3 = -2.759285104469687e+02
a4 = 1.383577518672690e+02
a5 = -3.066479806614716e+01
a6 = 2.506628277459239e+00
b1 = -5.447609879822406e+01
b2 = 1.615858368580409e+02
b3 = -1.556989798598866e+02
b4 = 6.680131188771972e+01
b5 = -1.328068155288572e+01
c1 = -7.784894002430293e-03
c2 = -3.223964580411365e-01
c3 = -2.400758277161838e+00
c4 = -2.549732539343734e+00
c5 = 4.374664141464968e+00
c6 = 2.938163982698783e+00
d1 = 7.784695709041462e-03
d2 = 3.224671290700398e-01
d3 = 2.445134137142996e+00
d4 = 3.754408661907416e+00
p_low = 0.02425
p_high = 1.0 - p_low


def inv_norm_cdf(p):
    """Estimates the inverse CDF for a normal distribution.

    Ported from http://home.online.no/~pjacklam/notes/invnorm/ (Peter
    John Acklam) and http://www.sultanik.com/Quantile_function (Evan
    Sultanik)

    Args:
        p: the lower tail probability
    """
    if 0 < p < p_low:
        # rational approximation for the lower region
        q = sqrt(-2 * log(p))
        x = ((((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) /
             ((((d1 * q + d2) * q + d3) * q + d4) * q + 1))
    elif p_low <= p <= p_high:
        # rational approximation for the central region
        q = p - 0.5
        r = q * q
        x = ((((((a1 * r + a2) * r + a3) * r + a4) * r + a5) * r + a6) * q /
             (((((b1 * r + b2) * r + b3) * r + b4) * r + b5) * r + 1.0))
    else:
        # rational approximation for the upper region
        q = sqrt(-2.0 * log(1.0 - p))
        x = (-(((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) /
             ((((d1 * q + d2) * q + d3) * q + d4) * q + 1.0))

    # Can't refine to maximum precision due to the lack of the erfc function.
    # See http://home.online.no/~pjacklam/notes/invnorm/ for details.
    return x


def inv_t_cdf(q, df):
    """Calculates the inverse CDF for the Student T's distribution.

    Ported from http://www.sultanik.com/Quantile_function (Evan
    Sultanik).
    Used with permission of Evan Sultanik.

    Args:
        q: The lower tail probability.
        df: Degrees of freedom.

    Notes:
        It is not exactly know if there is any problems with this
        implementation as I simplify fixed the implementation from
        sultanik.com with the R implementation without applying a lot of
        fixes from the R code as a) I'm not sure what they do, b) the
        approximation seem to be okay compared against scipy's
        implementation, and c) i'm not sure how i can rip out the
        function from all the R stuff.

        I've tested the errors from a q value of 0.50 to 1.0 (the valid
        range, increment of 0.001) with df from 1 to 149. The average
        err is 5.60e-6 max error being 0.00865 and a stddev of 9.04e-5.

        For more details, check https://gist.github.com/shuhaowu/6177897
    """

    if q < 0.5 or q > 1:
        raise ValueError("q value must be [0.5, 1]")

    # The function below calculates using a two tail value. Hence we need to
    # convert.
    p = (1 - q) * 2

    # There is a paper describing the operation of this algorithm
    # and it is behind a paywall:
    # http://dl.acm.org/citation.cfm?id=362776

    if df < 1:
        raise ValueError("df value must be >= 1")

    if df == 1:
        p *= pi / 2
        return cos(p) / sin(p)

    a = 1.0 / (df - 0.5)
    b = 48 / (a * a)
    c = ((20700 * a / b - 98) * a - 16) * a + 96.36
    d = ((94.5 / (b + c) - 3.0) / b + 1.0) * sqrt(a * pi / 2) * df

    x = d * p
    y = x ** (2.0 / df)
    if y > a + 0.05:
        # asymptotic inverse expansion about the normal
        x = inv_norm_cdf(p * 0.5)
        y = x * x
        if df < 5:
            c += 0.3 * (df - 4.5) * (x + 0.6)
        c = (((0.5 * d * x - 0.5) * x - 7.0) * x - 2.0) * x + b + c
        y = (((((0.4 * y + 6.3) * y + 36) * y + 94.5) / c - y - 3) / b + 1) * x
        y *= a * y
        if y > 0.002:
            y = exp(y) - 1
        else:
            y += 0.5 * y * y
    else:
        y = (((1 / (((df + 6) / (df * y) - 0.089 * d - 0.822) *
             (df + 2.0) * 3.0) + 0.5 / (df + 4.0)) * y - 1.0) *
             (df + 1.0) / (df + 2.0) + 1.0 / y)

    return sqrt(df * y)


class BasicModel(object):
    """Base models used by all models to see if something is explosive."""
    def __init__(self, data):
        """Initializes and trains the model.

        Do not override this method, override .train instead.

        Args:
            data: the data in a list
        """
        self.data = data
        self.t = range(len(self.data))
        self.train()

    def is_explosive(self, observed):
        """Checks if the next day value is explosive.

        Args:
            observed: The observed value of the next day/time period.

        Returns:
            A boolean indicating if something is explosive.
        """
        raise NotImplementedError

    def probability_of_significance(self, observed):
        """The probability of the observed value being explosive.

        Args:
            observed: The observed value of the next day/time period.

        Returns:
            A float from 0 to 1
        """
        raise NotImplementedError

    def train(self):
        """Trains the data. Called from __init__."""
        pass


class PredictiveModel(BasicModel):
    """Base model for any models that uses prediction."""
    def predict(self, t):
        """Predict the values of a time value.

        Note that the time values are not whatever time unit you're
        using. The model uses array indexes as time values. So if you
        have the data [3, 4, 10], t of 0 corresponds to 3, 1 to 4,
        and 2 to 10.

        Implement this function.

        Args:
            t: the time value.

        Returns:
            The predicted value at time t as a number.
        """
        raise NotImplementedError

    def predict_next(self):
        """A shortcut function for self.predict(self.t[-1] + 1).

        This essentially predicts the next day/next time's value.
        """
        return self.predict(self.t[-1] + 1)

    def prediction_err(self, t):
        """The prediction error of calling .predict(t).

        Implement this function.

        Args:
            t: time value

        Return:
            an error value.
        """
        raise NotImplementedError

    def prediction_err_next(self):
        """A shortcut function for self.prediction_err(self.t[-1] + 1)."""
        return self.prediction_err(self.t[-1] + 1)

    def is_explosive(self, observed):
        return observed - self.predict_next() > self.prediction_err_next()

    def probability_of_significance(self, observed):
        # should be getting the residuals and finding the probability from the
        # normal distribution
        raise NotImplementedError


class SlopeBased(BasicModel):
    """Slope based model uses slope check for explosiveness.

    This model automatically picks a threshold based on previous deviations.

    Formula:

        \\frac{y_t - y_{t-1}}{y_{t-1}} > t \sigma

    Where \sigma is the standard deviation of the left side of the
    formula for the last x days and t is the t statistics based on x and
    MIN_EXPLOSIVE_CONFIDENCE

    """
    MIN_EXPLOSIVE_CONFIDENCE = 0.9999

    def train(self):
        slopes = []
        for i in xrange(1, len(self.data)):
            slopes.append((self.data[i] - self.data[i - 1]) / self.data[i - 1])

        # Mean should be ~0
        self.mean = mean(slopes)
        self.deviation = std(slopes)
        t = inv_t_cdf(self.MIN_EXPLOSIVE_CONFIDENCE, len(slopes) - 1)
        self.threshold = self.deviation * t

    def is_explosive(self, next_value):
        d = (next_value - self.data[-1]) / self.data[-1]
        return d - self.mean > self.threshold

    def probability_of_significance(self, observed):
        pass


MODELS = {
    "SlopeBased": SlopeBased
}


SQL_SELECT = """
SELECT
    signature_id,
    date_processed::date AS report_date,
    count(*)
FROM
    reports_clean
WHERE
    date_processed >= DATE '{start}' AND date_processed::date <= DATE '{end}'
GROUP BY
    signature_id, date_processed::date
"""

SQL_INSERT = """
INSERT INTO suspicious_crash_signatures
    (signature_id, report_date)
VALUES
    ('{signature_id}', '{date}'::timestamp without time zone)
"""


class SuspiciousCrashesApp(PostgresBackfillCronApp):
    app_name = 'suspicious-crashes'
    app_version = '1.0'
    app_description = 'Finds explosive crashes for each day.'

    required_config = Namespace()

    required_config.add_option(
        'training_data_length',
        default=10,
        doc='the number of days of training data to feed to the models.'
    )

    required_config.add_option(
        'data_bin_length',
        default=24,
        doc='The number of hours for each bin to aggregate for crash counts.'
    )

    required_config.add_option(
        'model',
        default='SlopeBased',
        doc='Model used for analysis. :Available: ' + ', '.join(MODELS.keys())
    )

    required_config.add_option(
        'min_count',
        default=1000,
        doc='Minimum number of logged crashes today to trigger analysis.'
    )

    def _add_explosive_entry(self, signature_id, date, connection):
        self.config.logger.info('{0} is explosive!!'.format(signature_id))
        cursor = connection.cursor()
        cursor.execute(SQL_INSERT.format(signature_id=signature_id,
                                         date=date.strftime('%Y-%m-%d')))

    def run(self, connection, date):
        logger = self.config.logger
        end = date
        today = end.date()
        start = end - datetime.timedelta(self.config.training_data_length)
        modelcls = MODELS.get(self.config.model)
        if modelcls is None:
            raise ValueError('Model {0} is invalid.'.format(self.config.model))

        cursor = connection.cursor()
        logger.info('Getting counts...')
        cursor.execute(SQL_SELECT.format(start=start.strftime('%Y-%m-%d'),
                                         end=end.strftime('%Y-%m-%d')))

        today_counts = {}
        historic_counts = {}
        for signature_id, report_date, count in cursor:
            if report_date == today:
                today_counts[signature_id] = count
            else:
                counts = historic_counts.setdefault(signature_id, {})
                counts[report_date.strftime('%Y-%m-%d')] = count

        logger.info('Finding explosive crashes with {0}'.format(modelcls))

        modified = False
        for signature_id, count in today_counts.iteritems():
            if count > self.config.min_count:
                counts = historic_counts.get(signature_id, {})
                _temp_current = start.date()

                # Makes sure each data has data.
                crash_counts = []
                while _temp_current < today:
                    c = counts.get(_temp_current.strftime('%Y-%m-%d'), 0)

                    # Preventing a division by 0 error.
                    c = max(0.00001, c)
                    crash_counts.append(c)
                    _temp_current += datetime.timedelta(1)

                model = modelcls(crash_counts)
                if model.is_explosive(count):
                    modified = True
                    self._add_explosive_entry(signature_id, today, connection)

        if modified:
            connection.commit()
