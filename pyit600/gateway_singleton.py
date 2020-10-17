"""Salus iT600 gateway API singleton."""

import aiohttp
import threading

from pyit600 import IT600Gateway


class IT600GatewaySingleton:
    __lock__ = threading.Lock()
    __instance__: IT600Gateway = None

    @staticmethod
    def get_instance(
            euid: str,
            host: str,
            port: int = 80,
            request_timeout: int = 5,
            session: aiohttp.client.ClientSession = None,
            debug: bool = False,
    ) -> IT600Gateway:
        if not IT600GatewaySingleton.__instance__:
            with IT600GatewaySingleton.__lock__:
                if not IT600GatewaySingleton.__instance__:
                    IT600GatewaySingleton.__instance__ = IT600Gateway(
                        euid=euid,
                        host=host,
                        port=port,
                        request_timeout=request_timeout,
                        session=session,
                        debug=debug
                    )
        return IT600GatewaySingleton.__instance__
