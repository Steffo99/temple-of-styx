"""
Module defining declaratively SQL tables via :mod:`sqlalchemy`.
"""

import uuid

import argon2
import authlib.integrations.sqla_oauth2
import secrets
import sqlalchemy as s
import sqlalchemy.orm as so
import sqlalchemy.schema as ss

from ..authn.password import a2ph


class Base(so.DeclarativeBase):
    """
    Declarative base of the project.
    """


class Person(Base):
    """
    A physical person who uses the service.
    """
    __tablename__ = "people"

    name: so.Mapped[str] = so.mapped_column(primary_key=True)
    avatar: so.Mapped[str] = so.mapped_column(default="https://raw.githubusercontent.com/starshardstudio/emblems/main/rendered/person.png")
    password: so.Mapped[str | None] = so.mapped_column()
    passkey_challenge: so.Mapped[bytes | None] = so.mapped_column()

    controls: so.Mapped["Control"] = so.relationship(back_populates="person")
    clients: so.Mapped["Client"] = so.relationship(back_populates="creator")

    def has_password(self) -> bool:
        return self.password is not None

    def has_passkey(self) -> bool:
        return False

    def auth_methods_count(self) -> int:
        return sum([
            self.has_password(),
            self.has_passkey(),
        ])

    def set_password(self, value: str) -> None:
        self.password = a2ph.hash(value)

    def check_password(self, value: str) -> bool:
        try:
            return a2ph.verify(self.password, value)
        except argon2.exceptions.VerifyMismatchError:
            return False

    def generate_passkey_challenge(self) -> None:
        self.passkey_challenge = secrets.token_bytes(128)

    def is_authenticated(self) -> bool:
        return True

    def is_active(self) -> bool:
        return bool(self.password)

    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return self.name
    
    def get_display_name(self) -> str:
        return self.name


class Control(Base):
    """
    Bridge table connecting :class:`Person` to :class:`Identity`.
    """
    __tablename__ = "control"

    id: so.Mapped[uuid.UUID] = so.mapped_column(primary_key=True, default=uuid.uuid4)

    person_name: so.Mapped["str"] = so.mapped_column(s.ForeignKey("people.name"))
    identity_name: so.Mapped["str"] = so.mapped_column(s.ForeignKey("identities.name"))

    person: so.Mapped["Person"] = so.relationship(back_populates="controls")
    identity: so.Mapped["Identity"] = so.relationship(back_populates="controlled_by")
    scopes: so.Mapped["Scope"] = so.relationship(back_populates="control")

    __table_args__ = (
        ss.UniqueConstraint(person_name, identity_name, name="bridge_person_identity"),
    )


class Scope(Base):
    """
    The OAuth2 scopes of an :class:`Identity` that can be :class:`Control`-led by a given :class:`Person`.
    """
    __tablename__ = "scopes"

    id: so.Mapped[uuid.UUID] = so.mapped_column(primary_key=True, default=uuid.uuid4)

    control_id: so.Mapped[uuid.UUID] = so.mapped_column(s.ForeignKey("control.id"))
    name: so.Mapped[str] = so.mapped_column()

    control: so.Mapped["Control"] = so.relationship(back_populates="scopes")


class Identity(Base):
    """
    An identity that the physical person decided to assume.
    """
    __tablename__ = "identities"

    name: so.Mapped[str] = so.mapped_column(primary_key=True)
    avatar: so.Mapped[str] = so.mapped_column(default="https://raw.githubusercontent.com/starshardstudio/emblems/main/rendered/user.png")

    controlled_by: so.Mapped["Control"] = so.relationship(back_populates="identity")
    tokens: so.Mapped["Token"] = so.relationship(back_populates="identity")

    def get_user_id(self):
        return self.name


class Token(Base, authlib.integrations.sqla_oauth2.OAuth2TokenMixin):
    """
    A OAuth2 token for an :class:`Identity`.
    """
    __tablename__ = "people_tokens"

    id: so.Mapped[uuid.UUID] = so.mapped_column(primary_key=True, default=uuid.uuid4)
    identity_name: so.Mapped[str] = so.mapped_column(s.ForeignKey("identities.name"))

    identity: so.Mapped["Identity"] = so.relationship(back_populates="tokens")


class Client(Base, authlib.integrations.sqla_oauth2.OAuth2ClientMixin):
    """
    A OAuth2 client registered by a :class:`Person`.
    """
    __tablename__ = "clients"

    id: so.Mapped[uuid.UUID] = so.mapped_column(primary_key=True, default=uuid.uuid4)
    creator_name: so.Mapped[str] = so.mapped_column(s.ForeignKey("people.name"))

    creator: so.Mapped["Person"] = so.relationship(back_populates="clients")


__all__ = (
    "Base",
    "Person",
    "Control",
    "Identity",
    "Token",
    "Client",
)
