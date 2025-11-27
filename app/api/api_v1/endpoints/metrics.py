"""
Wrapper module for metrics endpoints.

This file keeps the previous import path stable (`app.api.api_v1.endpoints.metrics`)
but delegates implementation to the `metrics_pkg` package.

It simply exports the `router` defined in `metrics_pkg.handlers`.
"""

from .metrics_pkg.handlers import router

__all__ = ["router"]