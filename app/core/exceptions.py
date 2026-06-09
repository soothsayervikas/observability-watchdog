class WatchdogError(Exception):
    """Base application error."""


class ConfigurationError(WatchdogError):
    """Raised when required settings are missing or invalid."""


class IngestionError(WatchdogError):
    """Raised when log ingestion fails validation."""


class DetectionError(WatchdogError):
    """Raised when analysis pipeline fails."""


class AnalysisInProgressError(DetectionError):
    """Raised when a concurrent analysis run is already active."""


class WebhookDeliveryError(WatchdogError):
    """Raised when webhook delivery exhausts retries."""


class AlertNotFoundError(WatchdogError):
    """Raised when an alert ID does not exist."""


class IngestionParseError(WatchdogError):
    """Raised when uploaded log content cannot be parsed."""
