"""Skema request Administrator; status mengikuti tombol di frontend."""
from typing import Literal

from pydantic import BaseModel


class AccountStatusUpdate(BaseModel):
    status_aktif: Literal["ACTIVE", "REJECTED", "SUSPENDED"]
