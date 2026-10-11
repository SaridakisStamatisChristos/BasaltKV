class BasaltKVError(Exception):
    """Base error for BasaltKV."""


class ClosedError(BasaltKVError):
    pass


class CorruptionError(BasaltKVError):
    pass


class FormatVersionError(CorruptionError):
    pass


class LockError(BasaltKVError):
    pass


class ReadOnlyError(BasaltKVError):
    pass


class TransactionError(BasaltKVError):
    pass


class SizeLimitError(BasaltKVError):
    pass
