#coding=utf-8
from __future__ import division

def mapValue(value, values1, values2):
    '''
    For a value provided with an initial set of reference values,
    returns a new one proportionally defined between a second set of values.
    '''
    lowValue1, highValue1 = values1
    lowValue2, highValue2 = values2

    delta1 = highValue1 - lowValue1
    delta2 = highValue2 - lowValue2
    if delta1 != 0:
        factor = (value - lowValue1) / delta1
        value = lowValue2 + (delta2 * factor)
    return value