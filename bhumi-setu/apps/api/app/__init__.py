"""BHUMISETU API application package.

One FastAPI process holds every domain service and the Celery workers import
the same service modules (design §3.3). "Component" in §3.2 therefore denotes a
module boundary, not a deployment boundary: the seams are import-time seams.
"""
