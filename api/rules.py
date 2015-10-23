
import logging
log = logging.getLogger('scitran.api.jobs')

import bson
import pymongo
import datetime

from . import base
from . import util


#
# {
#   At least one match from this array must succeed, or array must be empty
#   "any": [
#       ["file.type",             "dicom"     ] # Match the file's type
#       ["file.name",             "*.dcm"     ] # Match a shell glob for the file name
#       ["file.measurements",     "diffusion" ] # Match any of the file's measurements
#       ["container.measurement", "diffusion" ] # Match the container's primary measurment
#       ["container.has-type",    "bvec"      ] # Match the container having any file (including this one) with this type
#   ]
#
#   All matches from array must succeed, or array must be empty
#   "all": [
#   ]
#
#   Algorithm to
#   "alg": "d2n"
# }
#

MATCH_TYPES = [
    'file.type',
    'file.name',
    'file.measurements',
    'container.measurement',
    'container.has-type'
]

def eval_match(match_type, match_param, file_, container):
    """
    Given a match entry, return if the match succeeded.
    """

    if not match_type in MATCH_TYPES:
        raise Exception('Unsupported match type ' + match_type)

    if match_type == 'file.type':
        pass
    elif match_type == 'file.name':
        pass
    elif match_type == 'file.measurements':
        pass
    elif match_type == 'container.measurement':
        pass
    elif match_type == 'container.has-type':
        pass
    else
        raise Exception('Unimplemented match type ' + match_type)


def eval_rule(rule, file_, container):
    """
    Decide if a rule should spawn a job.
    """

    # Are there matches in the 'any' set?
    must_match = len(rule.get('any', [])) > 0
    has_match = False

    for match in rule.get('any', []):
        if eval_match(match[0], match[1], file_, container):
            has_match = True
            break

    # If there were matches in the 'any' array and none of them succeeded
    if must_match and not has_match:
        return False

    # Are there matches in the 'all' set?
    for match in rule.get('all', []):
        if not eval_match(match[0], match[1], file_, container):
            return False

    return True


def check_rules(db, file_, container):
    """
    Check all rules that apply to this file.
    """

    rules = []

    # TODO: fetch rules from the project

    for rule in rules:
        if eval_rule(rule, file_, container):

