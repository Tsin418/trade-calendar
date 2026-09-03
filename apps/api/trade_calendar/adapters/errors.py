class AdapterError(Exception):
    code = "adapter_error"
    retryable = False


class NetworkError(AdapterError):
    code = "network_error"
    retryable = True


class HttpStatusError(AdapterError):
    code = "http_status_error"
    retryable = True


class RateLimitError(HttpStatusError):
    code = "rate_limited"


class PayloadTooLargeError(AdapterError):
    code = "payload_too_large"


class StructureChangedError(AdapterError):
    code = "structure_changed"


class ParseError(AdapterError):
    code = "parse_error"


class AuthenticationError(AdapterError):
    code = "authentication_error"


class TimezoneError(ParseError):
    code = "timezone_error"


class EmptyResultError(AdapterError):
    code = "unexpected_empty_result"
