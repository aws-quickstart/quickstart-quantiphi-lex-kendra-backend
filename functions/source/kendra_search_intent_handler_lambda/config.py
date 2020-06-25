"""
File for Slot configuration
"""

ORIGINAL_VALUE = 0
TOP_RESOLUTION = 1

SLOT_CONFIG = {
    'time': {'type': ORIGINAL_VALUE, 'remember': True},
    'problem': {'type': TOP_RESOLUTION, 'remember': True, 'error': 'I didn\'t understand "{}".'},
    'emp_id': {'type': ORIGINAL_VALUE, 'remember': True}
}


class SlotError(Exception):
    """
    Error raised when slot could not be resolved.
    """
