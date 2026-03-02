from __future__ import annotations

from typing import Dict, Optional, Protocol


class UserAuthPort(Protocol):
    def require_user(self, authorization: Optional[str] = None) -> Optional[Dict[str, object]]: ...
