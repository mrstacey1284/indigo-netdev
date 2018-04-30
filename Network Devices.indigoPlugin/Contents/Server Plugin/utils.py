## Utility methods for validating parameters

import re

# a basic regex for matching simple hostnames and IP addresses
re_hostname = re.compile('^(\w[\-\.]?)+$')

# a regex for matching MAC addresses of the form MM:MM:MM:SS:SS:SS
# Windows-like MAC addresses are also supported (MM-MM-MM-SS-SS-SS)
re_macaddr = re.compile('^([0-9a-fA-F][0-9a-fA-F][:\-]){5}([0-9a-fA-F][0-9a-fA-F])$')

################################################################################
def validateConfig_URL(key, values, errors, emptyOk=False):
    # TODO verify correct URL format
    return validateConfig_String(key, values, errors, emptyOk)

################################################################################
def validateConfig_MAC(key, values, errors, emptyOk=False):
    value = values.get(key, None)

    # it must first be a valid string
    if not validateConfig_String(key, values, errors, emptyOk):
        return False

    if re_macaddr.match(value) is None:
        errors[key] = 'invalid MAC address: %s' % value
        return False

    return True

################################################################################
def validateConfig_Hostname(key, values, errors, emptyOk=False):
    value = values.get(key, None)

    # it must first be a valid string
    if not validateConfig_String(key, values, errors, emptyOk):
        return False

    if re_hostname.match(value) is None:
        errors[key] = 'invalid hostname: %s' % value
        return False

    return True

################################################################################
def validateConfig_String(key, values, errors, emptyOk=False):
    value = values.get(key, None)

    if value is None:
        errors[key] = '%s cannot be empty' % key
        return False

    if not emptyOk and len(value) == 0:
        errors[key] = '%s cannot be blank' % key
        return False

    return True

################################################################################
def validateConfig_Int(key, values, errors, min=None, max=None):
    value = values.get(key, None)
    if value is None:
        errors[key] = '%s is required' % key
        return False

    intVal = None

    try:
        intVal = int(value)
    except:
        errors[key] = '%s must be an integer' % key
        return False

    if min is not None and intVal < min:
        errors[key] = '%s must be greater than or equal to %d' % (key, min)
        return False

    if max is not None and intVal > max:
        errors[key] = '%s must be less than or equal to %d' % (key, max)
        return False

    return True

