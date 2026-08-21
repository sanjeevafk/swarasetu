"""Primary Health Centre facility and ASHA assignment models."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class PHC(Base):
    __tablename__ = "phcs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, default="Bihar")
    facility_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PHC"
    )  # PHC | CHC | SubCenter | District Hospital
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="108")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_24x7: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    doctor_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hours: Mapped[str] = mapped_column(String(60), nullable=False, default="9 AM - 5 PM")

    asha_workers: Mapped[list["AshaAssignment"]] = relationship(back_populates="phc")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "district": self.district,
            "state": self.state,
            "facility_type": self.facility_type,
            "phone": self.phone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_24x7": self.is_24x7,
            "doctor_available": self.doctor_available,
            "hours": self.hours,
        }


class AshaAssignment(Base):
    """Community health worker (ASHA/ANM) attached to a PHC catchment area."""

    __tablename__ = "asha_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asha_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    village: Mapped[str] = mapped_column(String(120), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phc_id: Mapped[int | None] = mapped_column(ForeignKey("phcs.id"), nullable=True)

    phc: Mapped[PHC | None] = relationship(back_populates="asha_workers")
