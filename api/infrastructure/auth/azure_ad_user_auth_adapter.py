from __future__ import annotations

from typing import Dict, Optional

from api.auth import require_user


class AzureADUserAuthAdapter:
    def require_user(self, authorization: Optional[str] = None) -> Optional[Dict[str, object]]:
        return require_user(authorization=authorization)
