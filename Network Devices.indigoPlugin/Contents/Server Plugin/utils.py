## Utility methods for validating parameters

################################################################################
def validateConfig_URL(key, values, errors, emptyOk=False):
    # TODO verify correct URL format
    return validateConfig_String(key, values, errors, emptyOk)

################################################################################
def validateConfig_MAC(key, values, errors, emptyOk=False):
    # TODO verify correct MAC format
    return validateConfig_String(key, values, errors, emptyOk)

################################################################################
def validateConfig_Hostname(key, values, errors, emptyOk=False):
    # TODO verify correct hostname
    return validateConfig_String(key, values, errors, emptyOk)

################################################################################
def validateConfig_String(key, values, errors, emptyOk=False):
    textVal = values.get(key, None)

    if textVal is None:
        errors[key] = '%s cannot be empty' % key
        return False

    if not emptyOk and len(textVal) == 0:
        errors[key] = '%s cannot be blank' % key
        return False

    return True

################################################################################
def validateConfig_Int(key, values, errors, min=None, max=None):
    textVal = values.get(key, None)
    if textVal is None:
        errors[key] = '%s is required' % key
        return False

    intVal = None

    try:
        intVal = int(textVal)
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

