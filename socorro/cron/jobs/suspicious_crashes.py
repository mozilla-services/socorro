from __future__ import division

import calendar
from datetime import timedelta, datetime
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
    Sultanik) and http://svn.r-project.org/R/trunk/src/nmath/qt.c (R).
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

    # Just don't even bother beyond this point. At least the normal cdf
    # stuff kinda made sense. There is a paper describing the operation
    # and it is behind a paywall:
    # http://dl.acm.org/citation.cfm?id=362776

    # Note that this may not be a full implementation and only one from
    # http://www.sultanik.com/Quantile_function but corrected as the original
    # implementation was incorrect.

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
    def __init__(self, data):
        self.data = data
        self.t = range(len(self.data))
        self.train()

    def is_explosive(self, observed):
        raise NotImplementedError

    def probability_of_significance(self, observed):
        raise NotImplementedError

    def train(self):
        pass


class PredictiveModel(BasicModel):
    def predict(self, t):
        raise NotImplementedError

    def predict_next(self):
        return self.predict(self.t[-1] + 1)

    def prediction_err(self, t):
        raise NotImplementedError

    def prediction_err_next(self):
        return self.prediction_err(self.t[-1] + 1)

    def is_explosive(self, observed):
        return observed - self.predict_next() > self.prediction_err_next()

    def probability_of_significance(self, observed):
        # should be getting the residuals and finding the probability from the
        # normal distribution
        raise NotImplementedError


class SlopeBased(BasicModel):
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


class Aggregator(object):
    def __init__(self, bin=24):
        self.bin = bin
        self.counts = {}

    def buckify(self, dt):
        timestamp = int(calendar.timegm(dt.timetuple()))
        window = self.bin * 3600
        return int(timestamp // window)

    def unbuckify(self, bucket):
        return datetime.fromtimestamp(bucket * self.bin * 3600)

    def incr(self, dt, count):
        bucket = self.buckify(dt)
        self.counts[bucket] = self.counts.get(bucket, 0) + count

    def crash_counts(self):
        return sorted(self.counts.items(), key=lambda v: v[0])


SQL_HISTORIC = """
SELECT
    signature,
    date_processed
FROM
    reports
WHERE
    date_processed >= DATE '{start}' AND date_processed < DATE '{end}'
ORDER BY date_processed desc
"""

SQL_TODAY = """
SELECT
    signature,
    date_processed
FROM
    reports
WHERE
    utc_day_is(date_processed, '{today}')
"""

SQL_INSERT = """
INSERT INTO suspicious_crash_signatures
    (signature, date)
VALUES
    ('{signature}', '{date}'::timestamp without time zone)
"""


class SuspiciousCrashesApp(PostgresBackfillCronApp):
    app_name = 'suspicious-crashes'

    required_config = Namespace()

    required_config.add_option(
        'training_data_length',
        default=10,
        doc='The number of days used for the training data feed to the models.'
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

    def _add_explosive_entry(self, signature, date, connection):
        self.config.logger.info('{0} is explosive!!'.format(signature))
        cursor = connection.cursor()
        cursor.execute(SQL_INSERT.format(signature=signature,
                                         date=date.strftime('%Y-%m-%d')))

    def run(self, connection, date):
        logger = self.config.logger
        end = date
        start = end - timedelta(self.config.training_data_length)
        modelcls = MODELS.get(self.config.model)
        if modelcls is None:
            raise ValueError('Model {0} is invalid.'.format(self.config.model))

        cursor = connection.cursor()
        logger.info('Getting today\'s crashes...')
        cursor.execute(SQL_TODAY.format(today=end.strftime('%Y-%m-%d')))

        logger.info('Aggregating today\'s crash counts...')
        today_counts = {}
        for signature, date in cursor:
            signature.strip()
            today_counts[signature] = today_counts.get(signature, 0) + 1

        logger.info('Getting historic crashes up to {0} days'.format(
                    self.config.training_data_length))

        cursor = connection.cursor()
        cursor.execute(SQL_HISTORIC.format(start=start.strftime('%Y-%m-%d'),
                                           end=end.strftime('%Y-%m-%d')))

        logger.info('Aggregating historic crashes...')
        aggregators = {}
        for signature, date in cursor:
            signature = signature.strip()
            if today_counts.get(signature, 0) > self.config.min_count:
                agg = aggregators.get(signature)
                if agg is None:
                    agg = Aggregator(self.config.data_bin_length)
                    aggregators[signature] = agg

                agg.incr(date, 1)

        logger.info('Finding explosive crashes for {0} signatures'.format(
                    len(aggregators)))

        modified = False
        for signature, agg in aggregators.iteritems():
            data = agg.crash_counts()
            buckets, data = zip(*data)
            model = modelcls(data)
            if model.is_explosive(today_counts[signature]):
                modified = True
                self._add_explosive_entry(signature, end, connection)

        if modified:
            connection.commit()
