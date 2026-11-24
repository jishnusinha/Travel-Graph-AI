from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import Field, field_validator

from app.schemas.common import APIModel, LocalEmail


class SignupIn(APIModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: LocalEmail
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginIn(APIModel):
    email: LocalEmail
    password: str
    remember_me: bool = True


class ForgotPasswordIn(APIModel):
    email: LocalEmail


class ResetPasswordIn(APIModel):
    token: str
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class ChangePasswordIn(APIModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PreferencesIn(APIModel):
    interests: list[str] = Field(default_factory=list)
    home_city: str = "Kolkata, India"
    currency: str = "INR"
    budget_min: int = 20000
    budget_max: int = 50000
    accommodation_style: str = "mid-range"
    transport_preference: str = "flights"
    ai_mode_preference: str = "demo"
    theme: str = "system"
    reduced_motion: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class ProfileUpdateIn(APIModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None


class PreferencesOut(APIModel):
    interests: list[Any] = Field(default_factory=list)
    home_city: str
    currency: str
    budget_min: int
    budget_max: int
    accommodation_style: str
    transport_preference: str
    ai_mode_preference: str
    theme: str
    reduced_motion: bool
    extra: dict[str, Any] = Field(default_factory=dict)


class UserOut(APIModel):
    id: str
    email: LocalEmail
    full_name: str
    phone: Optional[str] = None
    timezone: str
    avatar_initials: str
    onboarding_completed: bool
    is_demo: bool
    created_at: datetime
    preferences: Optional[PreferencesOut] = None
    csrf_token: Optional[str] = None
