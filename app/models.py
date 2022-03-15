import builtins
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# from enum import auto
from flask import Markup, url_for
from flask_appbuilder import Model
from flask_appbuilder.filemanager import get_file_original_name
from flask_appbuilder.models.decorators import renders
from flask_appbuilder.models.mixins import AuditMixin, FileColumn, ImageColumn
from mortgage import Loan
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    func,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relation, relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.schema import PrimaryKeyConstraint

from app import db

relationship_property_contact = Table(
    "property_contact",
    Model.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("property_id", ForeignKey("property.id"), primary_key=True),
    Column("contact_id", ForeignKey("contact.id"), primary_key=True),
)


class Booking(Model):
    """Represents a vacation booking."""

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contact.id"))
    income_id = Column(Integer, ForeignKey("income.id"))
    property_id = Column(Integer, ForeignKey("property.id"), nullable=False)
    contact = relationship("Contact", backref="bookings")
    income = relationship("Income", backref="bookings")
    property = relationship("Property", backref="bookings")
    nightly_rate = Column(Float)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    url = Column(String(255))
    notes = Column(Text)

    def __repr__(self):
        return f"{self.contact.full_name} booking {self.start_date} through {self.end_date}"

    @builtins.property
    def days(self):
        return (self.end_date - self.start_date).days

    @builtins.property
    def revenue(self):
        nightly_rate = float(self.nightly_rate)
        nightly_fee = self.property.management_fee / 100 * nightly_rate
        nightly_revenue = nightly_rate - nightly_fee
        return nightly_revenue * self.days


class Contact(Model):
    """Tracks people associated with properties, mortgages, expenses, and income."""

    __table_args__ = (UniqueConstraint("first_name", "last_name"),)
    id = Column(Integer, primary_key=True)
    # booking_id = Column(Integer, ForeignKey("booking.id"))
    mortgage_id = Column(Integer, ForeignKey("mortgage.id"))
    mortgage = relationship("Mortgage")
    # expense_id = Column(Integer, ForeignKey("expense.id"))
    expenses = relationship("Expense", backref="contact")
    income_id = Column(Integer, ForeignKey("income.id"))
    income = relationship("Income")
    first_name = Column(String(20), nullable=False)
    last_name = Column(String(20), nullable=False)
    company = Column(String(60))
    phone = Column(String(20))
    email = Column(String(120))
    role = Column(String(30))

    def __repr__(self):
        return self.full_name

    @hybrid_property
    def full_name(self):
        """Returns the full name of a contact for convenience."""

        return self.first_name + " " + self.last_name


class Expense(Model, AuditMixin):
    """Tracks expenses associated with a property."""

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("property.id"))
    property = relationship("Property")
    contact_id = Column(Integer, ForeignKey("contact.id"))
    amount = Column(Float, nullable=False)
    tax = Column(Float, default=0, nullable=False)
    payee = Column(String(30), nullable=False)
    description = Column(Text)
    date = Column(Date)
    tax_deduction = Column(Boolean, default=True)
    receipt = Column(FileColumn)

    def __repr__(self):
        return f"${self.amount:,.2f} owed to {self.payee}"

    def receipt_file_name(self):
        return get_file_original_name(str(self.receipt))

    @renders("receipt")
    def receipt_link(self):
        if not self.receipt:
            return None
        url = url_for("static", filename="uploads/" + self.receipt)
        return Markup(f'<a href="{url}">{self.receipt_file_name()}</a>')


class Income(Model, AuditMixin):
    """Tracks income associated with a property."""

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("property.id"))
    property = relationship("Property")
    amount = Column(Float, nullable=False)
    payer = Column(String(30), nullable=False)
    date = Column(Date)

    def __repr__(self):
        return f"$(self.amount:,.2f) owed by {self.payer}"


class Inventory(Model, AuditMixin):
    """Inventory of the items in a property."""

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("property.id"))
    property = relationship("Property", backref="inventory")
    item = Column(String(30), nullable=False)
    description = Column(Text)
    cost = Column(Float, default=0.0, nullable=False)
    has_tax = Column(Boolean, default=True)
    sales_tax = Column(Float, default=0.0, nullable=False)
    purchase_date = Column(Date)
    quantity = Column(Integer, default=0, nullable=False)
    quality = Column(
        Enum("New", "Used", "Worn", "Damaged"), default="New", nullable=False
    )
    category = Column(String(30))
    location = Column(String(30))
    brand = Column(String(30))

    def __repr__(self):
        return self.item

    @builtins.property
    def calculated_sales_tax(self):
        """Calculate the sales tax for the cost of the item using the city and state of its associated property."""
        property = self.property
        tax_rate = (
            db.session.query(Tax)
            .filter_by(city=property.city, state=property.state)
            .scalar()
            .sales_rate
        )
        tax = self.cost * tax_rate
        if self.has_tax and (self.sales_tax != tax):
            self.sales_tax = tax
            db.session.add(self)
            db.session.commit()
        return tax

    @hybrid_property
    def total_cost(self):
        """The total cost for the given quantity of items."""
        return self.cost * self.quantity


class Link(Model):
    """A link to a URL associated with a property."""

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("property.id"))
    property = relationship("Property", backref="links")
    url = Column(Text, nullable=False)
    text = Column(String(255))

    def __repr__(self):
        return Markup(
            f'<a href="{self.url}">{self.text if self.text else self.url}</a>'
        )


class Mortgage(Model, AuditMixin):
    """Represents a mortgage for a property."""

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("property.id"))
    property = relationship("Property", backref=backref("mortgage", uselist=False))
    amount = Column(Float, nullable=False)
    term = Column(Integer, nullable=False)
    rate = Column(Float, nullable=False)
    down_payment = Column(Float, nullable=False)
    closing = Column(Float, nullable=False)
    lender = Column(String(30))
    start_date = Column(Date)
    has_insurance = Column(Boolean)
    has_PMI = Column(Boolean)
    has_tax = Column(Boolean)

    def __repr__(self):
        return f"${self.amount:,.0f} for {self.term} years at {self.rate:.2f}% with {self.down_payment:.0f}% down."

    @builtins.property
    def monthly_payment(self):
        """Calculates the monthly payment including fees, insurance, and taxes if specified."""
        monthly_rate = self.rate / 100 / 12
        periods = self.term * 12
        principal = self.amount - (self.down_payment / 100) * self.amount
        payment = (
            principal
            * (monthly_rate * (1 + monthly_rate) ** periods)
            / ((1 + monthly_rate) ** periods - 1)
        )
        if self.has_insurance and self.property:
            payment += self.property.insurance / 12
        if self.has_tax and self.property:
            payment += self.property.tax / 12
        return payment

    def amortization_schedule(self, start=None, end=None):
        """Provides data from the amortization schedule for the mortage."""
        principal = self.amount * (1 - (self.rate / 100))
        loan = Loan(principal=principal, interest=self.rate / 100, term=self.term)
        if not start and not end:
            return loan.schedule()
        schedule = loan.schedule()
        if start < self.start_date or end > self.start_date + timedelta(
            days=365.25 * self.term
        ):
            return


class Property(Model, AuditMixin):
    """Represents a piece of real estate."""

    id = Column(Integer, primary_key=True)
    contacts = relationship(
        "Contact", secondary=relationship_property_contact, backref="properties"
    )
    address = Column(Text, unique=True, nullable=False)
    city = Column(String(30), nullable=False)
    state = Column(String(20), nullable=False)
    zipcode = Column(String(10), nullable=False)
    cost = Column(Float)
    land_value = Column(Float, default=0)
    # mortgage_id = Column(Integer, ForeignKey("mortgage.id"), unique=True)
    # mortgage = relationship("Mortgage", backref="property", uselist=False)
    tax = Column(Float)
    association_fee = Column(Float)
    management_fee = Column(Float)
    insurance = Column(Float)
    description = Column(Text)
    nightly_rate = Column(Float)
    occupancy = Column(Integer)
    rent = Column(Float)

    def __repr__(self):
        return self.address

    def depreciation(self, year):
        """Calculate the annual depreciation for the property for a given year.

        Uses the residential depreciation rate of 27.5 years.
        """
        start = self.mortgage.start_date
        end = start + relativedelta(years=27, months=6)
        if year < start.year or year > end.year:
            return 0
        try:
            base = self.cost + self.mortgage.closing - self.land_value
        except AttributeError:
            base = self.cost + self.mortgage.closing - self.land_value
        if year == start.year:
            months = 13 - start.month
        elif year == end.year:
            months = end.month
        else:
            months = 12
        amount = base * (months / 330)
        return amount

    @property
    def list_links(self):
        """Returns a list of links related to the property."""
        count = len(self.links)
        if count == 0:
            return
        elif count == 1:
            return Markup(self.links[0])
        elif count >= 2:
            value = "<ul>\n"
            for link in self.links:
                value += f"<li>{link}</li>\n"
            value += "</ul>\n"
            return Markup(value)

    @property
    def tax_deduction(self):
        """The total tax deductable expenses plus depreciation.

        Includes expenses marked with tax_deduction == True.
        """
        result = (
            db.session.query(
                func.year(Expense.date),
                func.sum(Expense.amount) + func.sum(Expense.tax),
            )
            .filter_by(property_id=self.id)
            .filter_by(tax_deduction=True)
            .group_by(func.year(Expense.date))
        )
        return {row[0]: row[1] + self.depreciation(row[0]) for row in result}

    @property
    def total_monthly_cost(self):
        """Calculates the total monthly cost of the property."""
        mortgage = self.mortgage
        total = 0
        if isinstance(mortgage, Mortgage):
            total += mortgage.monthly_payment
        if isinstance(mortgage, Mortgage) and not mortgage.has_insurance:
            total += self.insurance / 12
        if isinstance(mortgage, Mortgage) and not mortgage.has_tax:
            total += self.tax / 12
        if self.management_fee > 0 and self.total_monthly_revenue > 0:
            total += (self.management_fee / 100) * self.total_monthly_revenue
        total += self.association_fee / 12
        return total

    @property
    def total_monthly_revenue(self):
        """Calculates the estimated total revenue from the property."""
        if self.occupancy is None:
            self.occupancy = 0
        if self.nightly_rate is None:
            self.nightly_rate = 0
        occupied_nights = (self.occupancy / 100) * 365
        revenue = self.nightly_rate * occupied_nights
        revenue /= 12
        return revenue

    @property
    def total_expenses(self):
        """Return the sum of all expenses for a property."""
        total = (
            db.session.query(func.sum(Expense.amount) + func.sum(Expense.tax))
            .filter_by(property_id=self.id)
            .first()[0]
        )
        return 0.0 if total is None else total

    @property
    def total_income(self):
        """Return the sum of all incomes for a property."""
        total = (
            db.session.query(func.sum(Income.amount))
            .filter_by(property_id=self.id)
            .scalar()
        )
        return 0.0 if total is None else total

    @property
    def total_inventory(self):
        """The cost of the entire inventory of the property."""
        total = (
            db.session.query(func.sum(Inventory.cost * Inventory.quantity))
            .filter_by(property_id=self.id)
            .scalar()
        )
        return total if total is not None else 0.0


class Tax(Model):
    """Sales tax rates for various cities."""

    id = Column(Integer, primary_key=True)
    city = Column(String(30))
    state = Column(String(30))
    sales_rate = Column(Float, default=0.0)
