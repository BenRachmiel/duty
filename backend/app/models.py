import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Table, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


person_tag = Table(
    "person_tag",
    Base.metadata,
    Column("person_id", Integer, ForeignKey("person.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)

duty_tag = Table(
    "duty_tag",
    Base.metadata,
    Column("duty_id", Integer, ForeignKey("duty.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    color: Mapped[str | None] = mapped_column(String(20))

    people: Mapped[list["Person"]] = relationship(secondary=person_tag, back_populates="tags")
    duties: Mapped[list["Duty"]] = relationship(secondary=duty_tag, back_populates="tags")


class Person(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    external_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tags: Mapped[list[Tag]] = relationship(secondary=person_tag, back_populates="people", lazy="selectin")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="person")


class Duty(Base):
    __tablename__ = "duty"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    date: Mapped[date] = mapped_column(Date)
    headcount: Mapped[int] = mapped_column(Integer, default=1)
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    difficulty: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tags: Mapped[list[Tag]] = relationship(secondary=duty_tag, back_populates="duties", lazy="selectin")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="duty")


class RuleType(str, enum.Enum):
    allow = "allow"
    deny = "deny"
    cooldown = "cooldown"


class Rule(Base):
    __tablename__ = "rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    person_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tag.id", ondelete="SET NULL"))
    duty_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tag.id", ondelete="SET NULL"))
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    cooldown_days: Mapped[int | None] = mapped_column(Integer)
    cooldown_duty_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tag.id", ondelete="SET NULL"))

    person_tag: Mapped[Tag | None] = relationship(foreign_keys=[person_tag_id], lazy="selectin")
    duty_tag: Mapped[Tag | None] = relationship(foreign_keys=[duty_tag_id], lazy="selectin")
    cooldown_duty_tag: Mapped[Tag | None] = relationship(foreign_keys=[cooldown_duty_tag_id], lazy="selectin")


class Assignment(Base):
    __tablename__ = "assignment"
    __table_args__ = (UniqueConstraint("person_id", "duty_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"), index=True)
    duty_id: Mapped[int] = mapped_column(ForeignKey("duty.id", ondelete="CASCADE"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    person: Mapped[Person] = relationship(back_populates="assignments", lazy="selectin")
    duty: Mapped[Duty] = relationship(back_populates="assignments", lazy="selectin")
