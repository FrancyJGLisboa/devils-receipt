"""Devil's Receipt — disconfirming-evidence OSINT.

State a belief; collect open-source evidence that would prove it WRONG, each
with a verifiable receipt (url + date + quote). Inverts confirmation-bias search.
"""

from .refute import collect, merge, ungrounded_quotes

__all__ = ["collect", "merge", "ungrounded_quotes"]
__version__ = "0.1.0"
