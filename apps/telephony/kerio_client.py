# apps/telephony/kerio_client.py
from __future__ import annotations

import os
import requests
from typing import Any, Dict, Optional


class KerioOperatorClient:
    def __init__(self) -> None:
        self.url = os.getenv("KERIO_OPERATOR_URL", "").strip()
        if not self.url:
            raise RuntimeError("KERIO_OPERATOR_URL is not set")

        self.username = os.getenv("KERIO_OPERATOR_USER", "").strip()
        self.password = os.getenv("KERIO_OPERATOR_PASS", "").strip()

        verify_env = os.getenv("KERIO_OPERATOR_SSL_VERIFY", "true").lower().strip()
        self.verify_ssl = verify_env in ("1", "true", "yes", "on")

        self.sess = requests.Session()
        self.token: Optional[str] = None
        self._rpc_id = 0

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params or {}}
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Token"] = self.token

        r = self.sess.post(self.url, json=payload, headers=headers, verify=self.verify_ssl, timeout=25)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"Kerio API error: {data['error']}")
        return data.get("result", {})

    def login(self) -> None:
        result = self._rpc("Session.login", {
            "userName": self.username,
            "password": self.password,
            "application": {"name": "ADLI", "vendor": "WEBadiko", "version": "1.0"},
        })
        token = result.get("token")
        if not token:
            raise RuntimeError("Kerio login failed: token not returned")
        self.token = token

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.token:
            self.login()
        try:
            return self._rpc(method, params=params)
        except Exception:
            self.login()
            return self._rpc(method, params=params)
