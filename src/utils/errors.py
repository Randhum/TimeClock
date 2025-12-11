"""
Error handling utilities for TimeClock application.
"""


class TimeClockError(Exception):
    """Base exception for TimeClock application"""
    pass


class EmployeeNotFoundError(TimeClockError):
    """Raised when an employee is not found"""
    pass


class InvalidActionError(TimeClockError):
    """Raised when an invalid clock action is attempted"""
    pass


class DatabaseError(TimeClockError):
    """Raised when a database operation fails"""
    pass


class RFIDError(TimeClockError):
    """Raised when an RFID operation fails"""
    pass


class ExportError(TimeClockError):
    """Raised when an export operation fails"""
    pass


class ValidationError(TimeClockError):
    """Raised when validation fails"""
    pass

