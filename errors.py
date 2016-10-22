
class PontiacError(Exception):
    """Base class for error conditions defined for this application"""
    pass


class ConfigurationError(PontiacError):
    """Exception class to denote an error in application configuration"""
    pass


class DataValidationError(PontiacError):
    """Exception class to denote an error in input data"""
    pass


class DependencyError(PontiacError):
    """Exception class to denote an error while trying to work with dependent
    services like databases, etc.
    """
    pass
